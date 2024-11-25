from flask import Flask, request, jsonify, send_file
from pyembroidery import read, write_png
from flask_cors import CORS
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

# Route to handle DST file upload and PNG generation
@app.route('/upload-dst', methods=['POST'])
def upload_dst():
    # Check if the file is included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    # Validate the file extension
    if file.filename.lower().endswith('.dst'):
        # Save the DST file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Generate PNG from DST
        output_png_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{os.path.splitext(file.filename)[0]}.png")
        try:
            pattern = read(file_path)
            write_png(pattern, output_png_path)  # Use pyembroidery to create a PNG

            # Retrieve thread colors
            thread_colors = []
            for thread in pattern.threadlist:
                # Append the color as RGB tuple
                thread_colors.append({
                    "red": thread.color.red,
                    "green": thread.color.green,
                    "blue": thread.color.blue
                })

            return jsonify({
                "png_path": output_png_path,
                "colors": thread_colors
            }), 200

        except Exception as e:
            return jsonify({"error": f"Failed to generate PNG: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Start the Flask server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
