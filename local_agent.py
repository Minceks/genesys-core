from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
# This is the FIX for the CORS error:
CORS(app, resources={r"/*": {"origins": "*"}})

PROJECT_ROOT = r"C:\Users\Matiss\vscode\ai agent\genesys-pro"

@app.route('/list-files', methods=['GET'])
def list_files():
    """Scans the project and returns the tree."""
    try:
        src_path = os.path.join(PROJECT_ROOT, "src")
        file_tree = {"routes": [], "components": []}
        
        # Scan routes
        r_path = os.path.join(src_path, "routes")
        if os.path.exists(r_path):
            file_tree["routes"] = [f for f in os.listdir(r_path) if f.endswith('.tsx')]
            
        # Scan components
        c_path = os.path.join(src_path, "components", "genesys")
        if os.path.exists(c_path):
            file_tree["components"] = [f for f in os.listdir(c_path) if f.endswith('.tsx')]
            
        return jsonify({"status": "success", "tree": file_tree})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/read-file', methods=['POST'])
def read_file():
    """Reads a file from the disk."""
    data = request.json
    filename = data.get('filename', '')
    # Ensure path is relative to root
    filename = filename.replace("src/", "src/")
    full_path = os.path.join(PROJECT_ROOT, filename)
    try:
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                return jsonify({"status": "success", "content": f.read()})
        return jsonify({"status": "error", "message": f"File {filename} not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/write-file', methods=['POST'])
def write_file():
    """Writes a file to the disk."""
    data = request.json
    filename = data.get('filename', '').replace("genesys-pro/", "")
    code = data.get('code', '')
    full_path = os.path.join(PROJECT_ROOT, filename)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"🚀 SUCCESS: Built {filename}")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print(f"⚡ BRIDGE ONLINE | Target: {PROJECT_ROOT}")
    app.run(port=5000)