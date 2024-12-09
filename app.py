from flask import Flask, request, jsonify
from pyembroidery import *
import urllib.parse
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Base URL for serving files
BASE_URL = 'https://dstupload.onrender.com'

# Function to read DST file and extract basic information
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    extras = pattern.extras
    thread_count = len(pattern.threadlist)
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    #dst with color
    pattern = EmbPattern()
    pattern.add_block([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)], "red")

    # Save the DST file in the uploads folder
    dst_filename = 'file.dst'
    dst_file_path = os.path.join(app.config['UPLOAD_FOLDER'], dst_filename)
    write_dst(pattern, dst_file_path)

    # Generate the URL for the DST file
    dst_url = f'{BASE_URL}/uploads/{urllib.parse.quote(dst_filename)}'

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "extras": extras,
        "dst_url": dst_url
    }

# Route to handle DST file upload and return information
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename.lower().endswith('.dst'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            # Get information about the DST file
            dst_info = get_dst_info(file_path)

            return jsonify(dst_info)
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

if __name__ == '__main__':
    app.run(debug=True)
