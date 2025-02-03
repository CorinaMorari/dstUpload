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

# Thread color palette based on your provided needles
THREAD_PALETTE = {
    1: "#000000",  # Emerald Black
    2: "#a51f37",  # Candy Apple Red
    3: "#5a2d8a",  # Regal Purple
    4: "#0f477a",  # Persian Blue
    5: "#3e87cb",  # Blue Jay
    6: "#008445",  # Celtic Green
    7: "#872b3a",  # Carmine
    8: "#2e3748",  # Night Sky
    9: "#aeb0af",  # Gray Haze
    10: "#898d8d", # Polished Pewter
    11: "#e4e9ff", # Super White
    12: "#ed5530", # Pumpkin
    13: "#f0b323", # Whipped Butterscotch
    14: "#606165", # Lead
    15: "#d5cb9f"  # Chamois
}

# Function to convert DST to TBF
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
    used_thread_numbers = set()

    for thread in pattern.threadlist:
        thread_number = thread.get_number()
        if thread_number in THREAD_PALETTE:  # Check if the thread is in the predefined palette
            thread_color = THREAD_PALETTE[thread_number]
            hex_colors.add(thread_color)
            used_thread_numbers.add(thread_number)

    # Generate the PNG file with the corresponding colors
    png_filename = os.path.splitext(os.path.basename(file_path))[0] + '.png'
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)

    # URL for the PNG file
    png_url = f'{BASE_URL}/uploads/pngs/{urllib.parse.quote(png_filename)}'

    return {"stitches": stitches, "threads": list(used_thread_numbers), "hex_colors": list(hex_colors), "png_file_url": png_url}

# Function to modify PNG color (if needed)
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

# Route to handle DST file upload and conversion to TBF
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

# Serve uploaded files
@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/pngs/<path:filename>', methods=['GET'])
def serve_png(filename):
    return send_from_directory(app.config['PNG_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
