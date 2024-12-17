from flask import Flask, request, jsonify
from pyembroidery import read, NEEDLE_SET
import os

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

    # Initialize stitch details and needle changes
    stitch_details = []
    needle_changes = []

    current_needle = None

    # Iterate over stitches and check for needle changes
    for stitch in pattern.stitches:
        stitch_data = {
            "position": (stitch.x, stitch.y),
            "command": stitch.command,
            "needle": stitch.needle,
        }

        # Capture needle change events
        if stitch.command == NEEDLE_SET and stitch.needle != current_needle:
            needle_changes.append({
                "needle": stitch.needle,
                "position": (stitch.x, stitch.y),
            })
            current_needle = stitch.needle
        
        stitch_details.append(stitch_data)

    # Extract basic thread information
    thread_count = len(pattern.threadlist)
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    return {
        "stitches": len(stitch_details),
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "stitch_details": stitch_details,
        "needle_changes": needle_changes
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
