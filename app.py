from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_tbf, write_png, EmbThread, read_tbf  # Assuming pyembroidery supports .tbf format
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

# Function to convert DST to TBF (instead of PES)
def convert_dst_to_tbf(dst_file_path):
    pattern = read(dst_file_path)

    tbf_file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(os.path.basename(dst_file_path))[0] + '.tbf')
    write_tbf(pattern, tbf_file_path)

    return tbf_file_path

# Function to parse TBF file, set thread colors, and generate PNG
def parse_tbf(file_path):
    pattern = read_tbf(file_path)
    stitches = []

    # Extract stitch information
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Extract the threads used in the TBF file
    threads = []
    hex_colors = set()
    print(pattern)
    for thread in pattern.threadlist:
        rgb = {"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()}
        threads.append(rgb)
        hex_colors.add(rgb_to_hex(rgb))  # Add HEX value to the set


    # Generate the PNG file
    png_filename = os.path.splitext(os.path.basename(file_path))[0] + '.png'
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)

    # URL for the PNG file
    png_url = f'{BASE_URL}/uploads/pngs/{urllib.parse.quote(png_filename)}'

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

# Route to handle DST file upload and conversion to TBF (instead of PES)
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename.lower().endswith('.dst'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            # Convert DST to TBF
            tbf_file_path = convert_dst_to_tbf(file_path)

            # Parse the TBF file to extract stitches, threads, and generate PNG
            parsed_data = parse_tbf(tbf_file_path)

            # Generate the URL for the TBF file
            tbf_file_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(tbf_file_path))}'

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

        return jsonify({
            "stitches": parsed_data["stitches"],
            "threads": parsed_data["threads"],
            "used_colors_hex": parsed_data["hex_colors"],
            "png_file_url": parsed_data["png_file_url"],
            "tbf_file_url": tbf_file_url  # Include TBF file URL in the response
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
        modified_png_url = f'{BASE_URL}/uploads/pngs/{urllib.parse.quote(os.path.basename(modified_png_path))}'

        return jsonify({
            "modified_png_url": modified_png_url
        })

    except Exception as e:
        return jsonify({"error": f"Failed to modify PNG color: {str(e)}"}), 500

# Route to update TBF thread colors (instead of PES)
@app.route('/update-tbf-threads', methods=['POST'])
def update_tbf_threads():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    hex_colors = request.form.get('hex_colors')

    if not hex_colors:
        return jsonify({"error": "Missing 'hex_colors' parameter"}), 400

    # Convert hex_colors from string to list
    try:
        hex_colors = eval(hex_colors)  # Convert string to list
        if not isinstance(hex_colors, list) or not all(isinstance(color, str) for color in hex_colors):
            raise ValueError
    except Exception:
        return jsonify({"error": "Invalid 'hex_colors' format. It must be a string representation of a list."}), 400

    if not file.filename.lower().endswith('.tbf'):
        return jsonify({"error": "Invalid file format. Please upload a .tbf file."}), 400

    # Save the uploaded TBF file
    tbf_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(tbf_file_path)

    try:
        # Read the TBF file
        pattern = read(tbf_file_path)

        # Update the threads in the TBF file based on the provided hex colors
        for i, hex_color in enumerate(hex_colors):
            if i < len(pattern.threadlist):  # Ensure we don't exceed the number of threads
                pattern.threadlist[i].set_hex_color(hex_color)

        # Save the updated TBF file
        updated_tbf_file_path = os.path.splitext(tbf_file_path)[0] + '_updated.tbf'
        write_tbf(pattern, updated_tbf_file_path)

        # Generate URL for the updated TBF file
        updated_tbf_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(updated_tbf_file_path))}'

        return jsonify({
            "tbf_file_url": updated_tbf_url  # Correctly returns the URL
        })
    except Exception as e:
        return jsonify({"error": f"Failed to update TBF threads: {str(e)}"}), 500

# Serve uploaded files
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/pngs/<path:filename>', methods=['GET'])
def serve_png(filename):
    return send_from_directory(app.config['PNG_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)
