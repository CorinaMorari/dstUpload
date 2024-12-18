from flask import Flask, request, jsonify
from pyembroidery import *
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

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors
    }

# Function to set needles for the DST file based on color changes
def set_needles_for_dst(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Initialize a counter for different needles and a set to store needles used
    needle_counter = 1
    used_needles = set()  # To track unique needles used
    last_thread = None

    # Iterate through the stitches and handle needle change
    for stitch in pattern.stitches:
        command = stitch[0]  # Command type

        # Debugging: print the stitch command to verify structure
        print(f"Stitch: {stitch}")

        if command == 3:  # Thread change command (needle_set)
            # Get the current thread (usually the 4th value in the stitch command)
            current_thread = stitch[3] if len(stitch) > 3 else None

            # Debugging: print the current thread
            print(f"Thread Change Detected: {current_thread}")

            if current_thread != last_thread:
                # Set the new needle
                pattern.add_command(encode_thread_change(SET_CHANGE_SEQUENCE, needle_counter))
                used_needles.add(needle_counter)  # Add the needle to the used set
                needle_counter += 1  # Increment needle for each thread change
                last_thread = current_thread

    # Write the updated pattern to a new DST file
    updated_dst_file_path = dst_file_path.replace(".dst", "_updated.dst")
    write_dst(pattern, updated_dst_file_path)

    return updated_dst_file_path, sorted(list(used_needles))

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

            # Set needles for the DST file and get the updated file path
            updated_file_path, used_needles = set_needles_for_dst(file_path)

            # Generate the downloadable URL for the updated file
            download_url = f"https://dstupload.onrender.com/{updated_file_path}"

            return jsonify({
                "dst_info": dst_info,
                "used_needles": used_needles,  # Return the needles used
                "download_url": download_url  # Provide the download URL for the updated file
            })
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

if __name__ == '__main__':
    app.run(debug=True)
