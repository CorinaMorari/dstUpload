import os

from flask import Flask, request, jsonify
from pyembroidery import read, NEEDLE_SET, END, COLOR_CHANGE

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
    thread_list = pattern.threadlist
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in
                     pattern.threadlist]

    # Analyze match commands
    needle_set_count = 0
    color_change_count = 0
    color_change_commands = []

    for command in pattern.get_match_commands(COLOR_CHANGE):
        color_change_count += 1
        color_change_command = command  # Store the current COLOR_CHANGE command

        # Add the color_change_command to the list
        color_change_commands.append(color_change_command)
        print(f"COLOR_CHANGE command at stitch {command}")

    for command in pattern.get_match_commands(NEEDLE_SET):
            needle_set_count += 1
            print(f"NEEDLE_SET command at stitch {command}")

    return {
        "stitches": stitches,
        "thread_list": thread_list,
        "thread_colors": thread_colors,
        "needle_set_count": needle_set_count,
        "color_change_count": color_change_count
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
