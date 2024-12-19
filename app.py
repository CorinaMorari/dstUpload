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
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    # Analyze match commands
    needle_set_count = 0
    color_change_count = 0
    last_color = None  # Track the last color used

    for command in pattern.get_match_commands(COLOR_CHANGE):
        color_change_count += 1
        current_color = pattern.get_color(command)  # Get the color at the COLOR_CHANGE command

        # If the color is different from the last color, we count it as a new needle set
        if last_color != current_color:
            print(f"COLOR_CHANGE command at stitch {command} with color {current_color}")
            last_color = current_color  # Update the last color
        else:
            print(f"COLOR_CHANGE command at stitch {command} (no color change)")

    # After processing color changes, track NEEDLE_SET commands and associate with the color changes
    for command in pattern.get_match_commands(NEEDLE_SET):
        if last_color is not None:
            needle_set_count += 1
            print(f"NEEDLE_SET command at stitch {command} after color change (color {last_color})")

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
