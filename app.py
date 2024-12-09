from flask import Flask, request, jsonify, send_file
from pyembroidery import read, write_dst, EmbThread
from flask_cors import CORS
import os
import random

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure folder for uploads
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

# Function to set random Madeira thread colors
def set_madeira_threads(pattern):
    for thread in pattern.threadlist:
        madeira_thread = random.choice(MADEIRA_THREADS)
        new_thread = EmbThread()
        new_thread.set_color(*madeira_thread["rgb"])
        new_thread.description = madeira_thread["name"]
        new_thread.catalog_number = madeira_thread["code"]
        thread.set(new_thread)

# Endpoint to upload DST and return updated DST with Madeira colors
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

        # Set Madeira Poly threads
        set_madeira_threads(pattern)

        # Save the updated DST file
        updated_dst_path = os.path.splitext(file_path)[0] + '_updated.dst'
        write_dst(pattern, updated_dst_path)

        # Return the updated file
        return send_file(
            updated_dst_path,
            as_attachment=True,
            download_name=os.path.basename(updated_dst_path),
            mimetype='application/octet-stream'
        )

    except Exception as e:
        return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
