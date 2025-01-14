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


def get_dst_info(dst_file_path, new_needle_numbers):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract stitches and threads
    stitches = len(pattern.stitches)
    thread_list = pattern.threadlist
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in thread_list]

    # Detect color change commands and extract initial needles
    color_change_indices = [i for i, stitch in enumerate(pattern.stitches) if stitch[2] & EmbConstant.COLOR_CHANGE]
    initial_needles = [pattern.stitches[i][2] & 0x0F for i in color_change_indices]

    # Get unique initial needles
    unique_initial_needles = list(sorted(set(initial_needles)))

    # Ensure sufficient new needle numbers are provided
    if len(new_needle_numbers) < len(unique_initial_needles):
        raise ValueError(f"Insufficient new needle numbers. Expected {len(unique_initial_needles)}, got {len(new_needle_numbers)}.")

    # Create a mapping from unique initial needle numbers to new needle numbers
    needle_mapping = {initial: new for initial, new in zip(unique_initial_needles, new_needle_numbers)}

    # Replace needles with new ones
    needle_set_info = []
    for color_change_index in color_change_indices:
        x, y, command = pattern.stitches[color_change_index]
        original_needle = command & 0x0F
        new_needle = needle_mapping.get(original_needle, original_needle)
        new_command = (command & ~0x0F) | (new_needle & 0x0F)
        pattern.stitches[color_change_index] = (x, y, new_command)
        needle_set_info.append({
            "stitch_position": color_change_index,
            "original_needle": original_needle,
            "new_needle": new_needle
        })

    # Save the updated DST file
    new_dst_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], 'updated_pattern.dst')
    write(pattern, new_dst_file_path)

    return {
        "stitches": stitches,
        "thread_list": thread_list,
        "thread_colors": thread_colors,
        "color_change_count": len(color_change_indices),
        "unique_initial_needles": unique_initial_needles,
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
