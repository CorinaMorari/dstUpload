from flask import Flask, request, jsonify
from pyembroidery import read, NEEDLE_SET, END, COLOR_CHANGE
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to read DST file and extract basic information
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_count = len(pattern.threadlist)
    thread_colors = [
        {"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()}
        for thread in pattern.threadlist
    ]

    # Analyze match commands
    used_needles = []
    needle_number = 1  # Start with the first needle

    # Inject NEEDLE_SET at the start and after every COLOR_CHANGE
    for stitch_index, command in enumerate(pattern.stitches):
        if stitch_index == 0:
            # Set the first needle at the start
            used_needles.append(needle_number)
            print(f"NEEDLE_SET: Needle {needle_number} set at the start (stitch {stitch_index})")
        elif command[0] == COLOR_CHANGE:
            # Increment the needle number
            needle_number += 1
            used_needles.append(needle_number)
            print(f"NEEDLE_SET: Needle {needle_number} set after COLOR_CHANGE at stitch {stitch_index}")

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "needle_numbers": used_needles
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
