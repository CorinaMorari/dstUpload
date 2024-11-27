from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_pes, write_png, EmbThread
from flask_cors import CORS
import os
import urllib.parse

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing (CORS)

# Configure upload and PNG folders
UPLOAD_FOLDER = './uploads'
PNG_FOLDER = './pngs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PNG_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PNG_FOLDER'] = PNG_FOLDER

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
    pes_file_path = os.path.splitext(dst_file_path)[0] + '.pes'
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
    png_filename = os.path.basename(file_path) + '.png'
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)

    # URL for the PNG file (adjust domain as necessary)
    base_url = 'https://dstupload.onrender.com'
    png_url = f'{base_url}/uploads/{urllib.parse.quote(png_filename)}'

    return {"stitches": stitches, "threads": threads, "hex_colors": list(hex_colors), "png_file_url": png_url}

# Function to convert RGB to HEX format
def rgb_to_hex(rgb):
    return f'#{rgb["r"]:02x}{rgb["g"]:02x}{rgb["b"]:02x}'

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

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

        return jsonify({
            "stitches": parsed_data["stitches"],
            "threads": parsed_data["threads"],
            "used_colors_hex": parsed_data["hex_colors"],
            "png_file_url": parsed_data["png_file_url"]
        })
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Route to serve the generated PNG file
@app.route('/uploads/<filename>', methods=['GET'])
def download_png(filename):
    return send_from_directory(app.config['PNG_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
