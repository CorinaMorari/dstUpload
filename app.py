from flask import Flask, request, jsonify
from pyembroidery import read, write, EmbThread
from pyembroidery.EmbConstant import HEADER_CONTROL
import os

# Initialize Flask app
app = Flask(__name__)

# Configure folders
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Predefined color palette
COLOR_PALETTE = [
    (213, 203, 159, "Chamois", "1305"),
    (96, 97, 101, "Lead", "1640"),
    (0, 132, 69, "Celtic Green", "1651"),
    (237, 85, 48, "Pumpkin", "1678"),
    (62, 135, 203, "Blue Jay", "1733"),
    (165, 31, 55, "Candy Apple Red", "1747"),
    (240, 179, 35, "Whipped Butterscotch", "1771"),
    (0, 0, 0, "Emerald Black", "1800"),
    (228, 233, 255, "Super White", "1801"),
    (174, 176, 175, "Gray Haze", "1810"),
    (15, 71, 122, "Persian Blue", "1843"),
    (137, 141, 141, "Polished Pewter", "1918"),
    (90, 45, 138, "Regal Purple", "1922"),
    (46, 55, 72, "Night Sky", "1976"),
    (135, 43, 58, "Carmine", "1981")
]

# Function to add random threads to a pattern if threadlist is empty
def add_random_threads(pattern):
    if not pattern.threadlist:
        for color in COLOR_PALETTE:
            thread = EmbThread()
            thread.set_color(color[0], color[1], color[2])
            thread.description = color[3]
            thread.catalog_number = color[4]
            pattern.add_thread(thread)

# Function to read DST file and extract detailed information
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Add random threads if threadlist is empty
    add_random_threads(pattern)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_count = len(pattern.threadlist)
    extras = pattern.extras if pattern.extras else {}

    return {
        "stitches": stitches,
        "thread_count": thread_count,
        "extras": extras
    }

# Function to create a new DST file with "TC" header
# Adds thread color information in the format: "#RRGGBB,Description,Catalog Number"
def create_dst_with_tc(file_path, output_path):
    pattern = read(file_path)

    # Add random threads if threadlist is empty
    add_random_threads(pattern)

    # Generate TC header with thread color information
    tc_data = []
    for thread in pattern.threadlist:
        color = f"#{thread.get_red():02X}{thread.get_green():02X}{thread.get_blue():02X}"
        description = thread.description if hasattr(thread, 'description') else "Unknown"
        catalog_number = thread.catalog_number if hasattr(thread, 'catalog_number') else "Unknown"
        tc_data.append(f"{color},{description},{catalog_number}")

    pattern.extras[HEADER_CONTROL] = "TC " + " ".join(tc_data)
    write(pattern, output_path)

# Route to handle DST file upload, process and create new file
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

            # Create new DST file with "TC" header
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"modified_{file.filename}")
            create_dst_with_tc(file_path, output_path)

            dst_info["modified_file"] = output_path

            return jsonify(dst_info)
        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

if __name__ == '__main__':
    app.run(debug=True)
