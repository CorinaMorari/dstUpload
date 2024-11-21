from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_svg, EmbThread
from flask_cors import CORS
import os

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Create necessary folders
UPLOAD_FOLDER = './uploads'
SVG_FOLDER = './svgs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SVG_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SVG_FOLDER'] = SVG_FOLDER

# Default threads (as EmbThread objects)
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

    # Extract stitch data
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Count color changes in the pattern
    color_change_count = sum(1 for stitch in pattern.stitches if stitch[2] == 1)  # Command 1 indicates color change

    # Assign only as many colors as needed
    if not pattern.threadlist:
        print(f"No threads found. Assigning {color_change_count} default colors.")
        pattern.threadlist = DEFAULT_THREADS[:max(1, color_change_count)]

    # Generate the SVG file
    svg_file_path = os.path.join(app.config['SVG_FOLDER'], os.path.basename(file_path) + '.svg')
    write_svg(pattern, svg_file_path)

    # Extract thread color data for response
    threads = [{"r": t.red, "g": t.green, "b": t.blue} for t in pattern.threadlist]

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

        base_url = 'https://dstupload.onrender.com'  # Your actual domain
        svg_url = f'{base_url}/download-svg/{os.path.basename(parsed_data["svg_file_path"])}'

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

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
