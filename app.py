from flask import Flask, request, jsonify
from pyembroidery import read, write, EmbPattern, COLOR_BREAK, SEQUENCE_BREAK
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to create a DST pattern with commands and stitches
def create_dst_pattern_with_commands():
    pattern = EmbPattern()

    # Adding COLOR_BREAK command and stitches
    pattern.add_command(COLOR_BREAK)
    print("Added COLOR_BREAK")
    pattern.add_stitch_relative(10, 0)  # Example stitch
    pattern.add_stitch_relative(0, 10)

    # Adding SEQUENCE_BREAK command and stitches
    pattern.add_command(SEQUENCE_BREAK)
    print("Added SEQUENCE_BREAK")
    pattern.add_stitch_relative(-10, 0)
    pattern.add_stitch_relative(0, -10)

    # Adding another COLOR_BREAK command and stitches
    pattern.add_command(COLOR_BREAK)
    print("Added COLOR_BREAK")
    pattern.add_stitch_relative(20, 20)

    # Adding another SEQUENCE_BREAK command and stitches
    pattern.add_command(SEQUENCE_BREAK)
    print("Added SEQUENCE_BREAK")
    pattern.add_stitch_relative(-20, -20)

    return pattern

# Route to generate a DST pattern and save it
@app.route('/generate-dst', methods=['POST'])
def generate_dst():
    try:
        # Create a pattern with commands and stitches
        pattern = create_dst_pattern_with_commands()

        # Save the DST file
        output_file = os.path.join(app.config['UPLOAD_FOLDER'], "generated_pattern.dst")
        write(pattern, output_file)

        return jsonify({"message": "DST pattern generated successfully", "file_path": output_file})
    except Exception as e:
        return jsonify({"error": f"Failed to generate DST pattern: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
