from flask import Flask, request, jsonify, send_from_directory
from pyembroidery import *
import urllib.parse
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Base URL for serving files
BASE_URL = 'https://dstupload.onrender.com'

# Function to create DST with color and generate the URL
def create_dst_with_color():
   # Create the pattern with color
    pattern = EmbPattern()
    pattern.add_block([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)], "red")
    # Define the color (red) using RGB values
red_thread = EmbThread(255, 0, 0)  # RGB for red

# Add a block to the pattern with the defined color
pattern.add_block([(0, 0), (0, 100), (100, 100), (100, 0), (0, 0)], red_thread)

    # Save the DST file in the uploads folder
    dst_filename = 'file.dst'
    dst_file_path = os.path.join(app.config['UPLOAD_FOLDER'], dst_filename)
    write_dst(pattern, dst_file_path)

    # Generate the URL for the DST file
    dst_url = f'{BASE_URL}/uploads/{urllib.parse.quote(dst_filename)}'

    return dst_url

# Route to handle serving uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Send the file from the uploads folder
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to create the DST with color and return the URL
@app.route('/create-dst', methods=['GET'])
def create_dst():
    try:
        dst_url = create_dst_with_color()
        return jsonify({"dst_url": dst_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
