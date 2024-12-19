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
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    # Analyze match commands and inject NEEDLE_SET after every COLOR_CHANGE
    needle_set_count = 0
    end_command_count = 0
    color_change_count = 0
    needle_number = 1
    needle_set_positions = []

    for stitch_index, command in enumerate(pattern.stitches):
        if command[0] == COLOR_CHANGE:
            # Increment the needle number and simulate NEEDLE_SET after COLOR_CHANGE
            color_change_count += 1
            needle_number += 1
            needle_set_positions.append(stitch_index + 1)  # Add NEEDLE_SET at the next stitch
            print(f"COLOR_CHANGE at stitch {stitch_index}, setting needle {needle_number}")

    # Log the positions where NEEDLE_SET commands are simulated
    for pos in needle_set_positions:
        needle_set_count += 1
        print(f"Simulated NEEDLE_SET command at stitch {pos}")

    # Count END commands
    for command in pattern.get_match_commands(END):
        end_command_count += 1
        print(f"END command at stitch {command}")

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "needle_set_count": needle_set_count,
        "end_command_count": end_command_count,
        "color_change_count": color_change_count,
        "needle_set_positions": needle_set_positions
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
