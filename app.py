import os
from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import *

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
DOWNLOAD_FOLDER = './downloads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER


# Function to read DST file, extract info, set needles, and generate a new DST file
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
    needle_number = 0
    color_change_commands = []
    set_needle = False  # Flag to indicate if the next stitch should set the needle number
    needle_set_info = []  # To store the set needle numbers and their positions

    for command in pattern.get_match_commands(COLOR_CHANGE):
        color_change_count += 1
        color_change_command = command  # Store the current COLOR_CHANGE command

        # Add the color_change_command to the list
        color_change_commands.append(color_change_command)
        print(f"COLOR_CHANGE command at stitch {command}")

    # Update needle set commands in the pattern
    for inx, stitch in enumerate(pattern.stitches):
        if set_needle or inx == 0:
            set_needle = False
            stitch[2] = EmbConstant.NEEDLE_SET | needle_number  # Set the needle
            needle_set_info.append({"needle_number": needle_number, "stitch_position": inx})
            needle_number += 1  # Increment the needle number

        # Check if the current stitch matches any color change command
        for color_change_command in color_change_commands:
            if stitch == color_change_command:
                set_needle = True
                print(f"Stitch {stitch} matches color change command at position {color_change_command}")

    # Count the NEEDLE_SET commands
    for command in pattern.get_match_commands(NEEDLE_SET):
        needle_set_count += 1
        print(f"NEEDLE_SET command at stitch {command}")

    # Save the modified pattern to a new DST file
    new_dst_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], 'updated_pattern.dst')
    write(pattern, new_dst_file_path)

    return {
        "stitches": stitches,
        "thread_list": thread_list,
        "thread_colors": thread_colors,
        "needle_set_count": needle_set_count,
        "color_change_count": color_change_count,
        "needle_set_info": needle_set_info,
        "new_dst_file": new_dst_file_path
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
            # Get information about the DST file and update the needles
            dst_info = get_dst_info(file_path)

            # Return information and the link to download the updated DST file
            return jsonify({
                "dst_info": dst_info,
                "download_link": f"/download/{os.path.basename(dst_info['new_dst_file'])}"
            })
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400


# Route to download the new DST file
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
