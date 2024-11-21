from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_svg, write_jef  # Importing additional embroidery format writer (JEF)
from flask_cors import CORS
import os
import xml.etree.ElementTree as ET

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Create an uploads directory if it doesn't exist
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# SVG output folder
SVG_FOLDER = './svgs'
os.makedirs(SVG_FOLDER, exist_ok=True)

# Configure SVG folder
app.config['SVG_FOLDER'] = SVG_FOLDER

# Define a simple color palette mapping (thread index to RGB)
THREAD_PALETTE = {
    1: {"r": 255, "g": 0, "b": 0},    # Red
    2: {"r": 0, "g": 255, "b": 0},    # Green
    3: {"r": 0, "g": 0, "b": 255},    # Blue
    4: {"r": 255, "g": 255, "b": 0},  # Yellow
    # Add more colors as needed based on your thread palette
}

# Function to parse DST file and generate SVG
def parse_dst(file_path):
    pattern = read(file_path)
    stitches = []
    threads = []

    # Extract stitch data from DST
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Extract thread colors from DST (using the color index and converting to RGB)
    for thread in pattern.threadlist:
        color_index = thread.color_index
        rgb = THREAD_PALETTE.get(color_index, {"r": 0, "g": 0, "b": 0})  # Default to black if index not found
        threads.append(rgb)

    # Generate the SVG file with .svg extension
    svg_file_path = os.path.join(app.config['SVG_FOLDER'], os.path.basename(file_path) + '.svg')
    write_svg(pattern, svg_file_path)

    # Parse the SVG file for stitches and threads
    svg_data = parse_svg(svg_file_path)

    return {"stitches": stitches, "threads": threads, "svg_file_path": svg_file_path, "svg_data": svg_data}

# Function to parse SVG and extract stitches and threads
def parse_svg(svg_file_path):
    # Parse the SVG file
    tree = ET.parse(svg_file_path)
    root = tree.getroot()

    # Extract stitches (in this case, paths or lines in the SVG)
    stitches = []
    for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
        d = path.attrib.get('d', '')
        stitches.append({"path": d})

    # Extract thread colors (using the stroke attribute for color)
    threads = []
    for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
        stroke_color = path.attrib.get('stroke', None)
        if stroke_color:
            threads.append(stroke_color)

    # Remove duplicates (if multiple stitches have the same color)
    threads = list(set(threads))

    return {"stitches": stitches, "threads": threads}

# Route to handle DST file upload and convert
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    # Check if the file is included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Validate the file extension
    if file.filename.lower().endswith('.dst'):
        # Process the DST file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)  # Save the file

        # Parse the DST file and generate SVG
        parsed_data = parse_dst(file_path)

        # Full URL to access the SVG
        base_url = 'https://dstupload.onrender.com'  # Your actual domain
        svg_url = f'{base_url}/download-svg/{os.path.basename(parsed_data["svg_file_path"])}'

        # Return the parsed data and the SVG file URL
        return jsonify({
            "stitches": parsed_data["stitches"],
            "threads": parsed_data["threads"],
            "svg_file_url": svg_url
        })
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Route to serve the SVG file
@app.route('/download-svg/<filename>', methods=['GET'])
def download_svg(filename):
    return send_from_directory(app.config['SVG_FOLDER'], filename)

# Route to update thread colors (this could be an API endpoint where the user updates the color)
@app.route('/update-thread-color', methods=['POST'])
def update_thread_color():
    # Get the thread index and new RGB values from the request
    data = request.get_json()
    thread_index = data.get('index')
    new_rgb = data.get('color')

    if thread_index and new_rgb:
        THREAD_PALETTE[thread_index] = new_rgb
        return jsonify({"message": "Thread color updated successfully"}), 200
    else:
        return jsonify({"error": "Invalid input. Please provide both 'index' and 'color'."}), 400

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
