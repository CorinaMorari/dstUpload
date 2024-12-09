from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import read, write_dst, EmbThread
from flask_cors import CORS
import os
import random

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure folder for uploads and processed DST files
UPLOAD_FOLDER = './uploads'
PROCESSED_FOLDER = './processed'  # Folder to store processed DST files
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Madeira Poly thread colors and codes
MADEIRA_THREADS = [
    {"code": "1305", "name": "Khaki", "rgb": (176, 158, 115)},
    {"code": "1801", "name": "White", "rgb": (255, 255, 255)},
    {"code": "1918", "name": "Grey", "rgb": (151, 151, 151)},
    {"code": "1976", "name": "Navy", "rgb": (11, 34, 66)},
    {"code": "1810", "name": "Light Grey", "rgb": (218, 218, 218)},
    {"code": "1640", "name": "Dark Grey", "rgb": (64, 64, 64)},
    {"code": "1771", "name": "Athletic Gold", "rgb": (255, 181, 66)},
    {"code": "1651", "name": "Kelly", "rgb": (0, 122, 51)},
    {"code": "1678", "name": "Orange", "rgb": (255, 120, 0)},
    {"code": "1733", "name": "Columbia Blue", "rgb": (91, 164, 221)},
    {"code": "1800", "name": "Black", "rgb": (0, 0, 0)},
    {"code": "1981", "name": "Maroon", "rgb": (128, 0, 0)},
    {"code": "1843", "name": "Royal", "rgb": (0, 52, 140)},
    {"code": "1922", "name": "Purple", "rgb": (92, 37, 120)},
    {"code": "1747", "name": "Cardinal", "rgb": (153, 0, 51)}
]

# Function to manually set Madeira thread colors for the pattern
def set_madeira_threads(pattern):
    thread_info = []  # List to store the thread information
    for stitch in pattern.stitches:
        madeira_thread = random.choice(MADEIRA_THREADS)
        new_thread = EmbThread()
        new_thread.set_color(*madeira_thread["rgb"])
        new_thread.description = madeira_thread["name"]
        new_thread.catalog_number = madeira_thread["code"]
        
        # Add thread info for the stitch
        thread_info.append({
            "name": new_thread.description,
            "code": new_thread.catalog_number,
            "rgb": new_thread.get_color()
        })
        stitch.thread = new_thread  # Assign the thread color to the stitch

    return thread_info

# Endpoint to preview thread information before uploading
@app.route('/preview-dst', methods=['POST'])
def preview_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if not file.filename.lower().endswith('.dst'):
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    try:
        # Read the DST file
        pattern = read(file_path)

        # Set Madeira Poly threads and get the thread info (preview)
        thread_info = set_madeira_threads(pattern)

        # Return the thread info for preview
        return jsonify({
            "message": "Preview created successfully",
            "thread_info": thread_info
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500


# Endpoint to upload DST and return a URL to the updated DST with Madeira colors
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if not file.filename.lower().endswith('.dst'):
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    try:
        # Read the DST file
        pattern = read(file_path)

        # Set Madeira Poly threads and get the thread info
        thread_info = set_madeira_threads(pattern)

        # Save the updated DST file
        updated_dst_path = os.path.join(app.config['PROCESSED_FOLDER'], os.path.splitext(file.filename)[0] + '_updated.dst')
        write_dst(pattern, updated_dst_path)

        # Generate the URL for the processed file
        file_url = f"https://dstupload.onrender.com/processed/{os.path.basename(updated_dst_path)}"

        # Return the URL to the updated DST file and thread info
        return jsonify({
            "message": "File processed successfully",
            "file_url": file_url,
            "thread_info": thread_info
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500

# Serve static files from the processed folder
@app.route('/processed/<filename>')
def processed_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
