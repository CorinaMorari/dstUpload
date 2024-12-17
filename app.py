from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import *
import os
import random

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to read DST file and extract detailed information
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Add random threads if threadlist is empty
    add_random_threads(pattern)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_count = len(pattern.threadlist)
    extras = pattern.extras if pattern.extras else {}

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "extras": extras
    }

# Function to create a new DST file with "TC" header
# Adds thread color information in the format: "#RRGGBB,Description,Catalog Number"
def create_dst_with_tc(file_path, output_path):
    pattern = read(file_path)

    # Extract CO value (thread count) from the pattern, adjust it if necessary
    co_value = pattern.extras.get("CO", len(pattern.threadlist))  # Default to the length of threadlist if CO is not present
    co_value = int(co_value) + 1  # Adjust CO to match the actual number of colors used

    # Create random needle assignments from 1 to 15
    used_needles = random.sample(range(1, 16), len(pattern.threadlist))  # Random needle numbers from 1 to 15

    # Update the pattern's needle assignments with random values
    for i, thread in enumerate(pattern.threadlist):
        thread.needle = used_needles[i]  # Assign new needle number

    # Save the modified DST file
    pattern.write(output_path)

    # Return the new needle assignments
    return used_needles

# Route to handle DST file upload, process and create new file
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

            # Create new DST file with random needle assignments
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"modified_{file.filename}")
            used_needles = create_dst_with_tc(file_path, output_path)

            # Prepare the response data
            dst_info["modified_file"] = f"https://dstupload.onrender.com/download/{file.filename}"
            dst_info["used_needles"] = used_needles

            return jsonify(dst_info)

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Route to handle file download
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
