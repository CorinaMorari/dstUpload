from flask import Flask, request, jsonify
from pyembroidery import read, write, NEEDLE_SET, END, COLOR_CHANGE
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to read DST file and extract basic information, and update with NEEDLE_SET
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_count = len(pattern.threadlist)
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    # Analyze commands and insert NEEDLE_SET after each COLOR_CHANGE
    updated_commands = []
    color_change_count = 0

    for command in pattern.stitches:
        updated_commands.append(command)

        # Check for COLOR_CHANGE and insert NEEDLE_SET
        if command[0] == COLOR_CHANGE:
            color_change_count += 1
            # Insert a NEEDLE_SET command
            updated_commands.append((NEEDLE_SET, 0, 0))  # Assuming default position (0, 0)

    # Replace the original commands with the updated ones
    pattern.stitches = updated_commands

    # Save the updated DST file for review (optional, for debugging)
    updated_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'updated_' + os.path.basename(dst_file_path))
    write(pattern, updated_file_path)

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "color_change_count": color_change_count,
        "updated_file_path": updated_file_path  # Path to updated file
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
