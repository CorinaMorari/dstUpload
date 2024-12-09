from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import *
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Base URL for serving files
BASE_URL = 'https://dstupload.onrender.com'

# Madeira colors (sample RGB values for Madeira threads)
madeira_colors = {
    "1305": (195, 178, 138),  # Khaki
    "1801": (255, 255, 255),  # White
    "1918": (169, 169, 169),  # Grey
    "1976": (0, 0, 128),      # Navy
    "1810": (211, 211, 211),  # Light Grey
    "1640": (169, 169, 169),  # Dark Grey
    "1771": (255, 185, 0),    # Athletic Gold
    "1651": (0, 128, 0),      # Kelly Green
    "1678": (255, 165, 0),    # Orange
    "1733": (0, 204, 255),    # Columbia Blue
    "1800": (0, 0, 0),        # Black
    "1981": (128, 0, 0),      # Maroon
    "1843": (0, 0, 255),      # Royal Blue
    "1922": (128, 0, 128),    # Purple
    "1747": (186, 12, 47),    # Cardinal Red
}

# Function to read DST file and extract basic information
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    extras = pattern.extras
    thread_count = len(pattern.threadlist)
    
    # Since threadlist is empty, we will return the RGB values manually set
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.stitches]

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "thread_colors": thread_colors,
        "extras": extras
    }

# Function to set Madeira colors in a DST file
def set_madeira_colors(dst_file_path):
    pattern = read(dst_file_path)

    # Manually assign thread colors based on Madeira thread codes
    current_color_index = 0  # To loop through Madeira colors
    for stitch in pattern.stitches:
        # Apply Madeira color based on index, looping through available colors
        madeira_thread_code = list(madeira_colors.values())[current_color_index % len(madeira_colors)]
        stitch.set_color(madeira_thread_code[0], madeira_thread_code[1], madeira_thread_code[2])
        
        # Increment the index for the next color
        current_color_index += 1

    # Save the updated file
    updated_dst_file_path = dst_file_path.replace(".dst", "_updated.dst")
    write_dst(pattern, updated_dst_file_path)

    return updated_dst_file_path

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
            # Get information about the DST file before modification
            dst_info_before = get_dst_info(file_path)

            # Apply Madeira colors and get the updated DST file path
            updated_dst_file_path = set_madeira_colors(file_path)

            # Get updated information after setting new Madeira colors
            dst_info_after = get_dst_info(updated_dst_file_path)

            # Return updated information and the new file path for download
            return jsonify({
                "before_update": dst_info_before,
                "after_update": dst_info_after,
                "download_link": f"{BASE_URL}/uploads/{os.path.basename(updated_dst_file_path)}"
            })

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Route to serve the updated DST file
@app.route('/uploads/<filename>')
def upload_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
