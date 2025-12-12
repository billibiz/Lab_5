from flask import Flask, jsonify
import os

app = Flask(__name__)

# Простой сервер для тестирования отказоустойчивости
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy", 
        "server": "server2",
        "port": 5001
    })

@app.route('/api/data', methods=['POST'])
def data():
    return jsonify({
        "message": "Data processed by server2",
        "port": 5001,
        "original_data": "test"
    })

if __name__ == '__main__':
    print("Server 2 starting on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=False)  # debug=False чтобы не конфликтовал с основным
