from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Используем HTTP для упрощения (серверы работают на HTTP в debug режиме)
server_urls = ['http://localhost:5000', 'http://localhost:5001', 'http://localhost:5002']

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка состояния всех серверов"""
    results = []
    
    for url in server_urls:
        try:
            response = requests.get(f"{url}/api/health", timeout=2)
            status = "up" if response.status_code == 200 else "down"
            results.append({"server": url, "status": status})
        except:
            results.append({"server": url, "status": "down"})
    
    return jsonify({
        "coordinator": "running",
        "servers": results,
        "up_count": sum(1 for r in results if r["status"] == "up")
    })

@app.route('/api/data', methods=['POST'])
def forward_request():
    """Перенаправление запроса на рабочий сервер"""
    data = request.get_json()
    
    for url in server_urls:
        try:
            response = requests.post(f"{url}/api/data", json=data, timeout=5)
            if response.status_code == 200:
                result = response.json()
                result["processed_by"] = url  # Добавляем информацию о сервере
                return jsonify(result), 200
        except:
            continue  # Пробуем следующий сервер
    
    return jsonify({"error": "All servers are down"}), 503

if __name__ == '__main__':
    print("🚀 Координатор запущен на порту 8000")
    print("📡 Управляет серверами:", server_urls)
    app.run(host='0.0.0.0', port=8000, debug=True)
