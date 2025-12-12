from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "server": "server3",
        "port": 5002
    })

@app.route('/api/data', methods=['POST'])
def data():
    return jsonify({
        "message": "Data processed by server3",
        "port": 5002,
        "original_data": "test"
    })

if __name__ == '__main__':
    print("Server 3 starting on port 5002...")
    app.run(host='0.0.0.0', port=5002, debug=False)
