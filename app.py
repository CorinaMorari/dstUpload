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

# Function to convert DST to PES
def convert_dst_to_pes(dst_file_path):
    pattern = read(dst_file_path)
    pes_file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(os.path.basename(dst_file_path))[0] + '.pes')
    write_pes(pattern, pes_file_path)
    return pes_file_path

# Predefined embroidery thread palette
PALETTE = [
    {"name": "Emerald Black", "hex": "#000000"},
    {"name": "Candy Apple Red", "hex": "#a51f37"},
    {"name": "Regal Purple", "hex": "#5a2d8a"},
    {"name": "Persian Blue", "hex": "#0f477a"},
    {"name": "Blue Jay", "hex": "#3e87cb"},
    {"name": "Celtic Green", "hex": "#008445"},
    {"name": "Carmine", "hex": "#872b3a"},
    {"name": "Night Sky", "hex": "#2e3748"},
    {"name": "Gray Haze", "hex": "#aeb0af"},
    {"name": "Polished Pewter", "hex": "#898d8d"},
    {"name": "Super White", "hex": "#e4e9ed"},
]

# Function to map PES threads to the predefined palette
def map_threads_to_palette(pattern):
    mapped_threads = []
    for i, thread in enumerate(pattern.threadlist):
        if i < len(PALETTE):
            palette_color = PALETTE[i]
            thread.set_hex_color(palette_color["hex"])
            mapped_threads.append({
                "needle": i + 1,
                "name": palette_color["name"],
                "hex": palette_color["hex"]
            })
    return mapped_threads

# Function to parse PES file
def parse_pes(file_path):
    pattern = read(file_path)
    threads = map_threads_to_palette(pattern)
    hex_colors = [t["hex"] for t in threads]
    png_filename = os.path.splitext(os.path.basename(file_path))[0] + '.png'
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)
    png_url = f'{BASE_URL}/pngs/{urllib.parse.quote(png_filename)}'
    return {
        "threads": threads,
        "hex_colors": hex_colors,
        "png_file_url": png_url
    }

# Function to convert HEX to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

# Function to modify PNG color
def modify_png_color(png_file_path, old_hex, new_hex):
    old_rgb = hex_to_rgb(old_hex)
    new_rgb = hex_to_rgb(new_hex)
    img = Image.open(png_file_path).convert("RGBA")
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            if pixels[x, y][:3] == old_rgb:
                pixels[x, y] = (new_rgb[0], new_rgb[1], new_rgb[2], pixels[x, y][3])
    modified_png_path = os.path.splitext(png_file_path)[0] + '_modified.png'
    img.save(modified_png_path)
    return modified_png_path

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
            pes_file_path = convert_dst_to_pes(file_path)
            parsed_data = parse_pes(pes_file_path)
            pes_file_url = f'{BASE_URL}/uploads/{urllib.parse.quote(os.path.basename(pes_file_path))}'
            return jsonify({
                "threads": parsed_data["threads"],
                "used_colors_hex": parsed_data["hex_colors"],
                "png_file_url": parsed_data["png_file_url"],
                "pes_file_url": pes_file_url
            })
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
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
    filename = os.path.basename(urllib.parse.unquote(png_url))
    png_file_path = os.path.join(app.config['PNG_FOLDER'], filename)
    if not os.path.exists(png_file_path):
        return jsonify({"error": "PNG file not found"}), 404
    try:
        modified_png_path = modify_png_color(png_file_path, old_hex, new_hex)
        modified_png_url = f'{BASE_URL}/pngs/{urllib.parse.quote(os.path.basename(modified_png_path))}'
        return jsonify({"modified_png_url": modified_png_url})
    except Exception as e:
        return jsonify({"error": f"Failed to modify PNG color: {str(e)}"}), 500

# Serve uploaded files
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Serve PNG files
@app.route('/pngs/<path:filename>', methods=['GET'])
def serve_png(filename):
    return send_from_directory(app.config['PNG_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
