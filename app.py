from flask import Flask, request, jsonify
from pyembroidery import read
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_count = len(pattern.threadlist)
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    # Extract detailed stitch data
    stitch_data = []
    current_needle = 1
    needle_sequence = []  # Keep track of needle usage order

    for stitch in pattern.stitches:
        command = stitch[0]  # Command type (e.g., JUMP, TRIM, THREAD_CHANGE, NORMAL)
        x = stitch[1]        # X-coordinate
        y = stitch[2]        # Y-coordinate

        # Add stitch data
        stitch_data.append({
            "command": command,
            "x": x,
            "y": y,
            "needle": current_needle
        })

        # Track needle changes for thread change commands (command 3 in DST files)
        if command == 3:  
            needle_sequence.append(current_needle)
            current_needle += 1

    # Ensure at least one needle is counted if no explicit thread change commands are present
    if not needle_sequence:
        needle_sequence = [1]

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "stitch_data": stitch_data,
        "needle_sequence": needle_sequence
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
