from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_png
from flask_cors import CORS
from PIL import Image
import os

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
BASE_URL = "http://localhost:8000/uploads/"  # Replace localhost with your server's domain or IP

def extract_colors_from_png(png_path):
    """Extract distinct colors from the generated PNG file."""
    try:
        image = Image.open(png_path)
        image = image.convert("RGB")  # Ensure the image is in RGB mode
        colors = image.getcolors(maxcolors=1000000)  # Extract all colors
        distinct_colors = sorted(set(color[1] for color in colors if color[0] > 0))
        return [{"red": r, "green": g, "blue": b} for r, g, b in distinct_colors]
    except Exception as e:
        return []

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

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
