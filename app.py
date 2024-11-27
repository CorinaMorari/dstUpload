from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_pes, write_png, EmbThread
from flask_cors import CORS
from PIL import Image
import os
import urllib.parse

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing (CORS)

# Configure folders
UPLOAD_FOLDER = './uploads'
PNG_FOLDER = './pngs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PNG_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PNG_FOLDER'] = PNG_FOLDER

# Base URL for serving files
BASE_URL = 'https://dstupload.onrender.com'

# Default threads (example RGB colors)
DEFAULT_THREADS = [
    EmbThread(0, 0, 0),  # Black
    EmbThread(255, 255, 255),  # White
    EmbThread(255, 0, 0),  # Red
    EmbThread(0, 255, 0),  # Green
    EmbThread(0, 0, 255),  # Blue
]


# Function to convert DST to PES
def convert_dst_to_pes(dst_file_path):
    pattern = read(dst_file_path)
    pes_file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(os.path.basename(dst_file_path))[0] + '.pes')
    write_pes(pattern, pes_file_path)
    return pes_file_path


# Function to parse PES file, set thread colors, and generate PNG
def parse_pes(file_path):
    pattern = read(file_path)
    stitches = []

    # Extract stitch information
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Extract the threads used in the PES file
    threads = []
    hex_colors = set()

    for thread in pattern.threadlist:
        rgb = {"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()}
        threads.append(rgb)
        hex_colors.add(rgb_to_hex(rgb))  # Add HEX value to the set

    # Generate the PNG file
    png_filename = os.path.splitext(os.path.basename(file_path))[0] + '.png'
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)

    # URL for the PNG file
    png_url = f'{BASE_URL}/uploads/{urllib.parse.quote(png_filename)}'

    return {"stitches": stitches, "threads": threads, "hex_colors": list(hex_colors), "png_file_url": png_url}


# Function to convert RGB to HEX format
def rgb_to_hex(rgb):
    return f'#{rgb["r"]:02x}{rgb["g"]:02x}{rgb["b"]:02x}'


# Function to modify PNG color
def modify_png_color(png_file_path, old_hex, new_hex):
    old_rgb = hex_to_rgb(old_hex)
    new_rgb = hex_to_rgb(new_hex)

    # Open the PNG image
    img = Image.open(png_file_path)
    img = img.convert("RGBA")  # Ensure the image is in RGBA mode

    # Get pixel data
    pixels = img.load()

    # Replace old color with the new one
    width, height = img.size
    for y in range(height):
        for x in range(width):
            current_color = pixels[x, y]
            if current_color[:3] == old_rgb:  # Ignore alpha channel
                pixels[x, y] = (new_rgb[0], new_rgb[1], new_rgb[2], current_color[3])

    # Save the modified image
    modified_png_path = os.path.splitext(png_file_path)[0] + '_modified.png'
    img.save(modified_png_path)

    return modified_png_path


# Function to convert HEX to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


# Route to handle DST file upload and conversion to PES
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename.lower().endswith('.dst'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            # Convert DST to PES
            pes_file_path = convert_dst_to_pes(file_path)

            # Parse the PES file to extract stitches, threads, and generate PNG
            parsed_data = parse_pes(pes_file_path)

            # Generate the URL for the PES file
            pes_file_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(pes_file_path))}'

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

        return jsonify({
            "stitches": parsed_data["stitches"],
            "threads": parsed_data["threads"],
            "used_colors_hex": parsed_data["hex_colors"],
            "png_file_url": parsed_data["png_file_url"],
            "pes_file_url": pes_file_url  # Include PES file URL in the response
        })
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400


# Route to modify PNG color
@app.route('/modify-png-color', methods=['POST'])
def modify_png_color_api():
    data = request.json
    png_url = data.get('png_url')
    old_hex = data.get('old_hex')
    new_hex = data.get('new_hex')

    if not png_url or not old_hex or not new_hex:
        return jsonify({"error": "Missing required parameters"}), 400

    # Decode the URL to handle any encoded spaces or characters
    decoded_png_url = urllib.parse.unquote(png_url)

    # Determine the local file path from the PNG URL
    filename = decoded_png_url.split("/")[-1]
    png_file_path = os.path.join(app.config['PNG_FOLDER'], filename)

    if not os.path.exists(png_file_path):
        return jsonify({"error": "PNG file not found"}), 404

    try:
        # Modify the PNG color
        modified_png_path = modify_png_color(png_file_path, old_hex, new_hex)

        # URL for the modified PNG file
        modified_png_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(modified_png_path))}'

        return jsonify({
            "modified_png_url": modified_png_url
        })

    except Exception as e:
        return jsonify({"error": f"Failed to modify PNG color: {str(e)}"}), 500

# Save PES file and return URL
@app.route('/convert_to_pes', methods=['POST'])
def convert_to_pes():
    try:
        # Retrieve file from the request
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file provided"}), 400

        # Save the uploaded file to the uploads directory
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Read the embroidery file
        emb = read(file_path)

        # Specify output PES file path
        pes_filename = os.path.splitext(file.filename)[0] + '.pes'
        pes_path = os.path.join(app.config['UPLOAD_FOLDER'], pes_filename)

        # Write the PES file
        write_pes(emb, pes_path, DEFAULT_THREADS)

        # Generate the PES file URL
        pes_url = f"{BASE_URL}/uploads/{pes_filename}"

        # Return the PES file URL in the response
        return jsonify({"pes_file_url": pes_url}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to convert file to PES: {str(e)}"}), 500


# Serve uploaded PES files
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_file(filename):
    try:
        # Decode the filename to handle encoded spaces
        decoded_filename = urllib.parse.unquote(filename)

        # Log the requested filename
        print(f"Requested file: {decoded_filename}")

        # Check if the requested file exists in the uploads directory
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], decoded_filename)

        if os.path.exists(file_path):
            print(f"Found file: {file_path}")
            return send_from_directory(app.config['UPLOAD_FOLDER'], decoded_filename)
        else:
            print(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404

    except Exception as e:
        # Log the error for debugging purposes
        print(f"Error occurred while serving file: {str(e)}")
        return jsonify({"error": f"Failed to serve file: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
