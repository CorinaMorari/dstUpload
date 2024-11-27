from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_pes, write_png, EmbThread, EmbPattern
from flask_cors import CORS
from PIL import Image
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

# Function to convert RGB to HEX format
def rgb_to_hex(rgb):
    return f'#{rgb["r"]:02x}{rgb["g"]:02x}{rgb["b"]:02x}'

# Function to convert HEX to RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

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

# Function to update threads based on hex color changes
def update_threads(pattern, hex_colors, threads):
    updated_threads = []

    for i, hex_color in enumerate(hex_colors):
        new_thread = EmbThread(threads[i]['r'], threads[i]['g'], threads[i]['b'])
        updated_threads.append(new_thread)
    
    # Apply the updated threads to the pattern
    pattern.threadlist = updated_threads
    return pattern

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
        base_url = 'https://dstupload.onrender.com'
        modified_png_url = f'{base_url}/uploads/{urllib.parse.quote(modified_png_path.split("/")[-1])}'

        return jsonify({
            "modified_png_url": modified_png_url
        })

    except Exception as e:
        return jsonify({"error": f"Failed to modify PNG color: {str(e)}"}), 500

# Route to create a new PES file
@app.route('/create-pes', methods=['POST'])
def create_pes():
    data = request.json
    stitches = data.get('stitches')
    threads = data.get('threads')
    hex_colors = data.get('hex_colors')

    if not stitches or not threads or not hex_colors:
        return jsonify({"error": "Missing required parameters: 'stitches', 'threads', or 'hex_colors'"}), 400

    # Create a new pattern
    pattern = EmbPattern()

    # Add threads
    for thread_data in threads:
        thread = EmbThread(thread_data['r'], thread_data['g'], thread_data['b'])
        pattern.add_thread(thread)

    # Update threads based on hex color changes
    pattern = update_threads(pattern, hex_colors, threads)

    # Add stitches
    for stitch_data in stitches:
        x, y, command = stitch_data['x'], stitch_data['y'], stitch_data['command']
        pattern.add_stitch(x, y, command)

    # Generate PES file
    pes_filename = 'generated_pattern.pes'
    pes_file_path = os.path.join(app.config['UPLOAD_FOLDER'], pes_filename)
    write_pes(pattern, pes_file_path)

    # Return PES file URL
    base_url = 'https://dstupload.onrender.com'
    pes_url = f'{base_url}/uploads/{urllib.parse.quote(pes_filename)}'

    return jsonify({"pes_file_url": pes_url})

# Route to serve the generated PES file
@app.route('/uploads/<filename>', methods=['GET'])
def download_pes(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
