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
def get_dst_info(dst_file_path, needle_numbers):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_list = pattern.threadlist
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    # Ensure there are enough needle numbers to assign
    color_change_commands = list(pattern.get_match_commands(COLOR_CHANGE))
    if len(needle_numbers) < len(color_change_commands) + 1:
        raise ValueError("The number of needle numbers provided is less than the number of color changes in the file.")

    # Set the first needle on stitch 0
    first_needle_number = needle_numbers[0]
    x, y, _ = pattern.stitches[0]
    pattern.stitches[0] = (x, y, EmbConstant.COLOR_CHANGE | first_needle_number)

    needle_set_info = [{"needle_number": first_needle_number, "stitch_position": 0}]
    needle_index = 1  # Start from the second needle

    # Set needles for each color change
    for command in color_change_commands:
        stitch_index = pattern.stitches.index(command)
        needle_number = needle_numbers[needle_index]

        # Get the original stitch (x, y, command)
        x, y, _ = pattern.stitches[stitch_index]

        # Update the stitch with the original coordinates and the new needle number
        pattern.stitches[stitch_index] = (x, y, EmbConstant.COLOR_CHANGE | needle_number)

        # Record the needle set info
        needle_set_info.append({"needle_number": needle_number, "stitch_position": stitch_index})
        needle_index += 1

    # Save the modified pattern to a new DST file
    new_dst_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], 'updated_pattern.dst')
    write(pattern, new_dst_file_path)

    return {
        "stitches": stitches,
        "thread_list": thread_list,
        "thread_colors": thread_colors,
        "color_change_count": len(color_change_commands),
        "needle_set_info": needle_set_info,
        "new_dst_file": new_dst_file_path
    }


# Route to handle DST file upload and return information
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Get the needle numbers from the request data
    needle_numbers = request.form.get('needle_numbers')

    # Parse the needle numbers into a list of integers
    if needle_numbers:
        try:
            needle_numbers = list(map(int, needle_numbers.split(',')))  # Convert comma-separated string to list of ints
        except ValueError:
            return jsonify(
                {"error": "Invalid needle numbers format. Ensure it's a comma-separated list of integers."}), 400
    else:
        return jsonify({"error": "No needle numbers provided."}), 400

    if file.filename.lower().endswith('.dst'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        try:
            # Get information about the DST file and update the needles
            dst_info = get_dst_info(file_path, needle_numbers)

            # Construct the download link with the domain
            download_link = f"https://dstupload.onrender.com/download/{os.path.basename(dst_info['new_dst_file'])}"

            # Return information and the link to download the updated DST file
            return jsonify({
                "dst_info": dst_info,
                "download_link": download_link
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
