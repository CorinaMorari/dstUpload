from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read
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

# Function to parse DST file and convert to SVG
def parse_dst(file_path):
    pattern = read(file_path)
    stitches = []
    threads = []

    # Extract stitch data
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Extract thread colors
    if pattern.threadlist:
        for thread in pattern.threadlist:
            threads.append({
                "r": thread.color.red,
                "g": thread.color.green,
                "b": thread.color.blue,
            })
    else:
        threads.append({"error": "No thread information available in this file."})

    # Convert to SVG and save
    svg_content = pattern.to_svg()
    svg_file_path = os.path.join(app.config['SVG_FOLDER'], os.path.basename(file_path) + '.svg')
    with open(svg_file_path, 'w') as svg_file:
        svg_file.write(svg_content)

    return {"stitches": stitches, "threads": threads, "svg_file_path": svg_file_path}

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
        parsed_data = parse_dst(file_path)

        # Return the parsed data and the SVG file path
        return jsonify({
            "stitches": parsed_data["stitches"],
            "threads": parsed_data["threads"],
            "svg_file_url": f'/download-svg/{os.path.basename(parsed_data["svg_file_path"])}'
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
