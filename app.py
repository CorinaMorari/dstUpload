from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_jef, write_svg  # Using pyembroidery for conversion
from flask_cors import CORS
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

# JEF and SVG output folders
JEF_FOLDER = './jefs'
SVG_FOLDER = './svgs'
os.makedirs(JEF_FOLDER, exist_ok=True)
os.makedirs(SVG_FOLDER, exist_ok=True)

# Configure JEF and SVG folders
app.config['JEF_FOLDER'] = JEF_FOLDER
app.config['SVG_FOLDER'] = SVG_FOLDER

# Function to parse DST file, convert to JEF and SVG, and extract stitches and thread info
def convert_dst_to_jef_and_svg(file_path):
    # Read the DST file using pyembroidery
    pattern = read(file_path)

    # Generate the JEF file
    jef_file_path = os.path.join(app.config['JEF_FOLDER'], os.path.basename(file_path) + '.jef')
    write_jef(pattern, jef_file_path)  # Convert DST to JEF

    # Generate the SVG file
    svg_file_path = os.path.join(app.config['SVG_FOLDER'], os.path.basename(file_path) + '.svg')
    write_svg(pattern, svg_file_path)  # Convert JEF to SVG

    # Extract stitches and threads from the pattern (JEF format)
    stitches = []
    threads = []
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    if pattern.threadlist:
        for thread in pattern.threadlist:
            threads.append({
                "r": thread.color.red,
                "g": thread.color.green,
                "b": thread.color.blue,
            })
    else:
        threads.append({"error": "No thread information available in this file."})

    return {
        "stitches": stitches,
        "threads": threads,
        "jef_file_path": jef_file_path,
        "svg_file_path": svg_file_path
    }

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

        # Convert DST to JEF and SVG
        converted_data = convert_dst_to_jef_and_svg(file_path)

        # Full URL to access the SVG and JEF files
        base_url = 'https://dstupload.onrender.com'  # Your actual domain
        svg_url = f'{base_url}/download-svg/{os.path.basename(converted_data["svg_file_path"])}'
        jef_url = f'{base_url}/download-jef/{os.path.basename(converted_data["jef_file_path"])}'

        # Return the parsed data and the SVG and JEF file URLs
        return jsonify({
            "stitches": converted_data["stitches"],
            "threads": converted_data["threads"],
            "jef_file_url": jef_url,
            "svg_file_url": svg_url
        })
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Route to serve the SVG file
@app.route('/download-svg/<filename>', methods=['GET'])
def download_svg(filename):
    return send_from_directory(app.config['SVG_FOLDER'], filename)

# Route to serve the JEF file
@app.route('/download-jef/<filename>', methods=['GET'])
def download_jef(filename):
    return send_from_directory(app.config['JEF_FOLDER'], filename)

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
