from flask import Flask, request, jsonify
from pyembroidery import read
from flask_cors import CORS  # Import CORS
import os

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app)

# Create an uploads directory if it doesn't exist
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to parse DST file
def parse_dst(file_path):
    pattern = read(file_path)
    stitches = []
    threads = []

    # Extract stitch data
    for stitch in pattern.stitches:
        x, y, command = stitch[0], stitch[1], stitch[2]
        stitches.append({"x": x, "y": y, "command": command})

    # Extract thread colors
    if pattern.threadlist:
        for thread in pattern.threadlist:
            threads.append({
                "r": thread.color.red,
                "g": thread.color.green,
                "b": thread.color.blue,
            })
    else:
        threads.append({"error": "No thread information available in this file."})

    return {"stitches": stitches, "threads": threads}

# Route to handle DST file upload
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    # Check if the file is included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Validate the file extension
    if file.filename.lower().endswith('.dst'):
        # Process the DST file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)  # Save the file

        # Parse the DST file
        parsed_data = parse_dst(file_path)
        return jsonify(parsed_data)
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
