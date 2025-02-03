import os
import urllib.parse
from flask import Flask, request, jsonify
from pes_parser import read, write_png  # Ensure you have this library
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "/opt/render/project/uploads"  # Adjust this path if needed
PNG_FOLDER = "/opt/render/project/uploads/pngs"  # PNG output folder
BASE_URL = "https://yourdomain.com"  # Replace with your actual domain

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PNG_FOLDER'] = PNG_FOLDER

# Ensure upload folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PNG_FOLDER, exist_ok=True)

def map_threads_to_palette(pattern):
    """Maps PES thread colors to a predefined palette."""
    predefined_palette = [
        {"hex": "#000000", "name": "Black"},
        {"hex": "#FF0000", "name": "Red"},
        {"hex": "#00FF00", "name": "Green"},
        {"hex": "#0000FF", "name": "Blue"},
        {"hex": "#FFFF00", "name": "Yellow"}
    ]

    threads = []
    for thread in pattern.threads:
        color_code = f'#{thread.color_code:06X}'  # Convert to HEX
        closest_match = min(predefined_palette, key=lambda t: abs(int(t["hex"][1:], 16) - int(color_code[1:], 16)))
        threads.append({"hex": closest_match["hex"], "name": closest_match["name"]})

    return threads

def parse_pes(file_path):
    """Parses a PES file and extracts thread colors, stitch count, and generates a PNG."""
    pattern = read(file_path)

    # Extract stitch count
    stitch_count = len(pattern.stitches)

    # Map threads to a predefined color palette
    threads = map_threads_to_palette(pattern)
    hex_colors = [t["hex"] for t in threads]

    # Generate PNG preview
    png_filename = os.path.splitext(os.path.basename(file_path))[0] + ".png"
    png_file_path = os.path.join(app.config['PNG_FOLDER'], png_filename)
    write_png(pattern, png_file_path)

    # Generate URL for the PNG file
    png_url = f"{BASE_URL}/uploads/pngs/{urllib.parse.quote(png_filename)}"

    return {
        "stitches": stitch_count,  # Now includes stitch count
        "threads": threads,
        "hex_colors": hex_colors,
        "png_file_url": png_url
    }

@app.route("/upload_dst", methods=["POST"])
def upload_dst():
    """Handles DST file uploads and returns parsed stitch & thread data."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Parse the PES file
    parsed_data = parse_pes(file_path)

    return jsonify({
        "stitches": parsed_data["stitches"],  # Now included
        "threads": parsed_data["threads"],
        "used_colors_hex": parsed_data["hex_colors"],
        "png_file_url": parsed_data["png_file_url"],
        "pes_file_url": f"{BASE_URL}/uploads/{urllib.parse.quote(filename)}"
    })

if __name__ == "__main__":
    app.run(debug=True)
