import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# IMPORTANT: Set this to the absolute path of your project root
PROJECT_ROOT = r'C:\Users\PC\SwarmMultiAgent'

# --- FIX: Accept both GET and POST methods ---
@app.route('/inspect', methods=['GET', 'POST']) 
def inspect_file():
    
    # --- FIX: Read path from POST JSON body or GET query parameters ---
    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"error": "Missing JSON body."}), 400
        data = request.get_json()
        filepath = data.get('path')
    else: # GET request
        filepath = request.args.get('path')
    
    if not filepath:
        return jsonify({"error": "Missing 'path' parameter."}), 400

    absolute_path = os.path.join(PROJECT_ROOT, filepath)
    
    # Security check: Ensure the path is within the project directory
    if not absolute_path.startswith(PROJECT_ROOT):
        return jsonify({"error": "Access denied. Path is outside project root."}), 403

    if not os.path.exists(absolute_path):
        return jsonify({"error": f"File not found: {filepath}"}), 404

    try:
        with open(absolute_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Limit content size to avoid overwhelming the LLM context
        if len(content) > 15000:
            content = content[:15000] + "\n... [CONTENT TRUNCATED]"
            
        return jsonify({"path": filepath, "content": content})
    except Exception as e:
        return jsonify({"error": f"Error reading file: {str(e)}"}), 500

if __name__ == '__main__':
    # Run on the fixed port, only accessible locally
    app.run(port=5001, host='127.0.0.1')