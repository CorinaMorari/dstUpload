from flask import send_from_directory

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

            # Prepare the thread list to return in the response
            thread_list = [{
                "color": f"#{thread.get_red():02X}{thread.get_green():02X}{thread.get_blue():02X}",
                "description": thread.description,
                "catalog_number": thread.catalog_number
            } for thread in read(output_path).threadlist]

            # Add the modified file and thread list to the response
            dst_info["modified_file"] = f"https://dstupload.onrender.com/download/{file.filename}"
            dst_info["thread_list"] = thread_list

            return jsonify(dst_info)

        except Exception as e:
            return jsonify({"error": f"Failed to process DST file: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a .dst file."}), 400

# Route to handle file download
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    # Send the modified file for download
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
