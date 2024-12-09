from flask import Flask, request, jsonify
from pyembroidery import read
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
    embroidery = read(dst_file_path)

    # Print out general data
    print("Pattern Information:")
    print(f"Stitch Count: {embroidery.get_stitch_count()}")  # Correct method for stitch count
    print(f"Width: {embroidery.width()}")  # Width of the pattern
    print(f"Height: {embroidery.height()}")  # Height of the pattern
    print(f"Thread Count: {len(embroidery.get_colors())}")  # Number of thread colors
    print(f"Thread Colors: {embroidery.get_colors()}")  # List of thread colors

    # Extract basic information
    stitches = embroidery.get_stitch_count()  # Correct method to get stitch count
    width = embroidery.width()  # Width of the embroidery
    height = embroidery.height()  # Height of the embroidery
    thread_count = len(embroidery.get_colors())  # Number of thread colors
    thread_colors = embroidery.get_colors()  # Get the thread colors

    return {
        "stitches": stitches,
        "width": width,
        "height": height,
        "thread_count": thread_count,
        "thread_colors": thread_colors
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
