from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_svg
from flask_cors import CORS  # Import CORS
import os

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

# Define default threads if empty (set specific colors as needed)
DEFAULT_THREADS = [
    {"r": 0, "g": 0, "b": 0},  # Black
    {"r": 255, "g": 255, "b": 255},  # White
    {"r": 255, "g": 0, "b": 0},  # Red
    {"r": 0, "g": 255, "b": 0},  # Green
    {"r": 0, "g": 0, "b": 255},  # Blue
]

# Function to parse DST file and generate SVG
def parse_dst(file_path):
    pattern = read(file_path)
    stitches = []

    # Extract stitch data
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Check if threadlist is empty and set default threads if necessary
    if not pattern.threads:
        print("No threads found, setting default threads.")
        # Assign the default threads to the pattern's threads
        pattern.threads = DEFAULT_THREADS

    # Return the updated pattern, stitches, and thread data
    svg_file_path = os.path.join(app.config['SVG_FOLDER'], os.path.basename(file_path) + '.svg')

    # Generate the SVG file with .svg extension, using the threads set above
    write_svg(pattern, svg_file_path)

    return {"stitches": stitches, "threads": pattern.threads, "svg_file_path": svg_file_path}

# Route to handle DST file upload
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
        try:
            parsed_data = parse_dst(file_path)
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

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

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
