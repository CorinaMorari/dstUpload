from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_png
from flask_cors import CORS
from PIL import Image
import os
import urllib.parse

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Create an uploads directory if it doesn't exist
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Base URL for accessing files
BASE_URL = "https://dstupload.onrender.com/uploads/"  # Updated domain


def extract_colors_from_png(png_path):
    """Extract distinct colors from the generated PNG file."""
    try:
        image = Image.open(png_path)
        image = image.convert("RGB")  # Ensure the image is in RGB mode
        colors = image.getcolors(maxcolors=1000000)  # Extract all colors
        if not colors:
            return []

        distinct_colors = sorted(set(color[1] for color in colors if color[0] > 0))
        return [{"red": r, "green": g, "blue": b} for r, g, b in distinct_colors]
    except Exception as e:
        return {"error": f"Failed to extract colors: {str(e)}"}


def change_colors_in_png(png_image, color_changes):
    """Change specific colors in the PNG image based on given color mappings."""
    try:
        img_data = png_image.load()  # Get pixel data

        for old_color, new_color in color_changes.items():
            # Convert colors to RGB tuples
            old_rgb = tuple(old_color)
            new_rgb = tuple(new_color)

            # Loop through the pixels and replace the old color with the new color
            for y in range(png_image.height):
                for x in range(png_image.width):
                    if img_data[x, y] == old_rgb:
                        img_data[x, y] = new_rgb

        return png_image

    except Exception as e:
        raise Exception(f"Error modifying PNG: {str(e)}")


# Route to serve static files from uploads directory
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    """Serve files from the uploads folder."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Route to handle DST file upload and PNG generation
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    # Check if the file is included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Validate the file extension
    if file.filename.lower().endswith('.dst'):
        # Save the DST file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Generate PNG from DST
        output_png_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{os.path.splitext(file.filename)[0]}.png")
        try:
            pattern = read(file_path)
            write_png(pattern, output_png_path)  # Use pyembroidery to create a PNG

            # Extract colors from the PNG
            colors = extract_colors_from_png(output_png_path)

            # Retrieve stitches
            stitches = [{"x": stitch[0], "y": stitch[1], "command": stitch[2]} for stitch in pattern.stitches]

            # Construct response
            response = {
                "png_url": f"{BASE_URL}{os.path.basename(output_png_path)}",
                "stitches": stitches,
                "colors": colors
            }

            return jsonify(response), 200

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400


# Route to change colors in an uploaded PNG
@app.route('/change-png-colors', methods=['POST'])
def change_png_colors():
    """Change colors in an existing PNG file."""
    # Get JSON data from the request
    data = request.get_json()

    # Check if 'png_url' and 'color_changes' are provided
    if not data or 'png_url' not in data or 'color_changes' not in data:
        return jsonify({"error": "Both 'png_url' and 'color_changes' are required."}), 400

    png_url = data['png_url']
    color_changes = data['color_changes']

    # Ensure the color changes are provided in the correct format
    if not isinstance(color_changes, dict):
        return jsonify({"error": "'color_changes' should be a dictionary mapping old colors to new ones."}), 400

    # Decode the URL path and extract the filename
    png_url_path = urllib.parse.urlparse(png_url).path
    png_filename = os.path.basename(png_url_path)
    decoded_filename = urllib.parse.unquote(png_filename)

    # Load the PNG image from the upload folder
    png_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)

    # Check if the file exists
    if not os.path.exists(png_path):
        print(f"File path does not exist: {png_path}")  # Debugging log
        return jsonify({"error": "PNG file not found."}), 404

    try:
        # Open the PNG file using PIL
        png_image = Image.open(png_path)

        # Change the colors in the PNG
        modified_png_image = change_colors_in_png(png_image, color_changes)

        # Save the modified image to a new file
        modified_png_path = os.path.join(app.config['UPLOAD_FOLDER'], 'modified_' + decoded_filename)
        modified_png_image.save(modified_png_path)

        # Return the URL of the modified PNG
        response = {
            "png_url": f"{BASE_URL}{os.path.basename(modified_png_path)}"
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Failed to modify PNG: {str(e)}"}), 500


# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
