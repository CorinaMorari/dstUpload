from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_svg, EmbThread
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = './uploads'
SVG_FOLDER = './svgs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SVG_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SVG_FOLDER'] = SVG_FOLDER

# Default threads
DEFAULT_THREADS = [
    EmbThread(0, 0, 0),  # Black
    EmbThread(255, 255, 255),  # White
    EmbThread(255, 0, 0),  # Red
    EmbThread(0, 255, 0),  # Green
    EmbThread(0, 0, 255),  # Blue
]

# Function to parse DST file and generate SVG
def parse_dst(file_path):
    pattern = read(file_path)
    stitches = []

    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Count the color change commands (command 1 indicates a color change)
    color_change_count = max(1, sum(1 for stitch in pattern.stitches if stitch[2] == 1))

    # Assign default threads if none are provided in the pattern
    if not pattern.threadlist:
        # Use enough default threads based on color changes, limited by available defaults
        pattern.threadlist = DEFAULT_THREADS[:min(len(DEFAULT_THREADS), color_change_count)]

    # Extract thread colors from the pattern
    threads = []
    for thread in pattern.threadlist:
        try:
            # Extract color from EmbThread object
            threads.append({"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()})
        except AttributeError:
            # Fallback for non-standard thread representations
            threads.append({"r": thread[0], "g": thread[1], "b": thread[2]})

    # Generate the SVG file with the pattern's thread colors
    svg_file_path = os.path.join(app.config['SVG_FOLDER'], os.path.basename(file_path) + '.svg')
    write_svg(pattern, svg_file_path)

    return {"stitches": stitches, "threads": threads, "svg_file_path": svg_file_path}

# Route to handle DST file upload
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename.lower().endswith('.dst'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            parsed_data = parse_dst(file_path)
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

        base_url = 'https://dstupload.onrender.com'  # Replace with your actual domain
        svg_url = f'{base_url}/download-svg/{os.path.basename(parsed_data["svg_file_path"])}'

        return jsonify({
            "stitches": parsed_data["stitches"],
            "threads": parsed_data["threads"],
            "svg_file_url": svg_url
        })
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

@app.route('/download-svg/<filename>', methods=['GET'])
def download_svg(filename):
    return send_from_directory(app.config['SVG_FOLDER'], filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
