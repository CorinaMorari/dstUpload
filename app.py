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

def parse_tbf(file_path, color_palette):
    pattern = read_tbf(file_path)
    stitches = []

    # Extract stitch information
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Replace threads from the provided color palette
    hex_colors = set()
    for i, thread in enumerate(pattern.threadlist):
        # If the palette has enough colors, replace the thread color
        if i < len(color_palette):
            hex_color = color_palette[i]
            rgb = hex_to_rgb(hex_color)
            thread.set_rgb(rgb['r'], rgb['g'], rgb['b'])
            hex_colors.add(hex_color)

    # Convert the set to a list for JSON response
    hex_colors = list(hex_colors)

    # Generate the PNG file
    png_filename = os.path.splitext(os.path.basename(file_path))[0] + '.png'
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)

    # URL for the PNG file
    png_url = f'{BASE_URL}/uploads/pngs/{urllib.parse.quote(png_filename)}'

    return {"stitches": stitches, "used_colors_hex": hex_colors, "png_file_url": png_url}


# Function to convert HEX to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return {
        "r": int(hex_color[0:2], 16),
        "g": int(hex_color[2:4], 16),
        "b": int(hex_color[4:6], 16)
    }

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

            # A predefined color palette (to be used in the TBF)
            color_palette = ["#FF5733", "#33FF57", "#3357FF"]  # Example colors, replace with actual palette

            # Parse the TBF file to extract stitches, threads, and generate PNG
            parsed_data = parse_tbf(tbf_file_path, color_palette)

            # Generate the URL for the TBF file
            tbf_file_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(tbf_file_path))}'

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

        return jsonify({
            "stitches": parsed_data["stitches"],
            "used_colors_hex": parsed_data["hex_colors"],
            "png_file_url": parsed_data["png_file_url"],
            "tbf_file_url": tbf_file_url  # Include TBF file URL in the response
        })
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

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
            else:
                # If more colors are provided than threads, break after updating all threads
                break

        # Save the updated TBF file
        updated_tbf_file_path = os.path.splitext(tbf_file_path)[0] + '_updated.tbf'
        write_tbf(pattern, updated_tbf_file_path)

        # Generate PNG for the updated TBF
        png_filename = os.path.splitext(os.path.basename(updated_tbf_file_path))[0] + '.png'
        png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
        write_png(pattern, png_file_path)

        # URL for the updated PNG file
        png_url = f'{BASE_URL}/uploads/pngs/{urllib.parse.quote(png_filename)}'

        # Generate URL for the updated TBF file
        updated_tbf_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(updated_tbf_file_path))}'

        return jsonify({
            "tbf_file_url": updated_tbf_url,
            "png_file_url": png_url  # Provide the new PNG URL
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
