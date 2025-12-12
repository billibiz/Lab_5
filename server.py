from flask import Flask, request, jsonify, session
import ssl
import os
import json
import time
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import pyotp
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Пути к сертификатам
CERT_DIR = 'certs'
SERVER_CERT = os.path.join(CERT_DIR, 'server_cert.pem')
SERVER_KEY = os.path.join(CERT_DIR, 'server_key.pem')
CA_CERT = os.path.join(CERT_DIR, 'ca_cert.pem')
CLIENT_CERT = os.path.join(CERT_DIR, 'client_cert.pem')
CLIENT_KEY = os.path.join(CERT_DIR, 'client_key.pem')
ENCRYPTION_KEY_FILE = 'encryption_key.txt'

# Проверка существования файлов сертификатов
def check_certificates():
    required_files = [SERVER_CERT, SERVER_KEY, CA_CERT, CLIENT_CERT, CLIENT_KEY]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"⚠️  Внимание: Файл {file_path} не найден!")
            return False
    return True

# Создание необходимых директорий и файлов
def setup_directories():
    if not os.path.exists(CERT_DIR):
        os.makedirs(CERT_DIR)
        print(f"📁 Создана директория: {CERT_DIR}")
    
    if not os.path.exists(ENCRYPTION_KEY_FILE):
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_FILE, 'wb') as f:
            f.write(key)
        print(f"🔑 Создан файл с ключом шифрования: {ENCRYPTION_KEY_FILE}")

# In-memory storage for demo purposes (in production, use a database)
users_db = {
    'user1': {
        'password': 'password123',
        'totp_secret': pyotp.random_base32(),
        'mfa_enabled': False,
        'failed_attempts': 0,
        'locked_until': None
    }
}

# Store TOTP secrets temporarily for setup
totp_secrets = {}

@app.before_request
def verify_client_cert():
    # Skip certificate verification for MFA endpoints during setup
    if request.path in ['/api/mfa/setup', '/api/mfa/verify', '/api/login', '/api/health']:
        return
    
    if 'authenticated' not in session or not session['authenticated']:
        return jsonify({'error': 'Authentication required'}), 401
    
    cert_data = request.get_json().get('certificate')
    if not cert_data:
        return jsonify({'error': 'Certificate required'}), 401
    
    if not verify_certificate(cert_data):
        return jsonify({'error': 'Invalid certificate'}), 401

def verify_certificate(cert_pem):
    try:
        certificate = load_pem_x509_certificate(cert_pem.encode(), default_backend())
        # In production, verify against CA
        return True
    except:
        return False

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if username not in users_db:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user = users_db[username]
    
    # Check if account is locked
    if user['locked_until'] and datetime.now() < user['locked_until']:
        return jsonify({'error': 'Account locked. Try again later.'}), 403
    
    # Verify password
    if user['password'] != password:
        user['failed_attempts'] += 1
        
        # Lock account after 3 failed attempts
        if user['failed_attempts'] >= 3:
            user['locked_until'] = datetime.now() + timedelta(minutes=15)
            users_db[username] = user
            return jsonify({'error': 'Too many failed attempts. Account locked for 15 minutes.'}), 403
        
        users_db[username] = user
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Reset failed attempts on successful password
    user['failed_attempts'] = 0
    users_db[username] = user
    
    # Check if MFA is enabled
    if user['mfa_enabled']:
        return jsonify({
            'message': 'Password accepted. MFA required.',
            'mfa_required': True,
            'username': username
        })
    else:
        # If MFA not enabled, ask user to set it up
        totp_secret = pyotp.random_base32()
        totp_secrets[username] = totp_secret
        
        # Generate QR code for setup
        totp = pyotp.TOTP(totp_secret)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name="Secure Distributed System"
        )
        
        # Generate QR code
        img = qrcode.make(provisioning_uri)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'message': 'Password accepted. MFA setup required.',
            'mfa_setup_required': True,
            'totp_secret': totp_secret,
            'qr_code': qr_code,
            'username': username
        })

@app.route('/api/mfa/setup', methods=['POST'])
def mfa_setup():
    data = request.get_json()
    username = data.get('username')
    token = data.get('token')
    
    if not username or not token:
        return jsonify({'error': 'Username and token required'}), 400
    
    if username not in totp_secrets:
        return jsonify({'error': 'Session expired. Please login again.'}), 401
    
    totp_secret = totp_secrets[username]
    totp = pyotp.TOTP(totp_secret)
    
    if totp.verify(token, valid_window=1):
        # Enable MFA for user
        users_db[username]['totp_secret'] = totp_secret
        users_db[username]['mfa_enabled'] = True
        
        # Clean up temporary secret
        del totp_secrets[username]
        
        return jsonify({
            'message': 'MFA setup successful',
            'mfa_enabled': True
        })
    else:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/mfa/verify', methods=['POST'])
def mfa_verify():
    data = request.get_json()
    username = data.get('username')
    token = data.get('token')
    
    if not username or not token:
        return jsonify({'error': 'Username and token required'}), 400
    
    if username not in users_db:
        return jsonify({'error': 'Invalid user'}), 401
    
    user = users_db[username]
    
    if not user['mfa_enabled']:
        return jsonify({'error': 'MFA not enabled for user'}), 400
    
    totp = pyotp.TOTP(user['totp_secret'])
    
    if totp.verify(token, valid_window=1):
        # Authentication successful
        session['authenticated'] = True
        session['username'] = username
        # Сохраняем время истечения сессии как строку ISO формата
        expires_time = (datetime.now() + timedelta(hours=1)).replace(tzinfo=None)
        session['expires'] = expires_time.isoformat()
        
        return jsonify({
            'message': 'Authentication successful',
            'session_token': 'generated-session-token',  # In production, generate JWT
            'expires_in': 3600
        })
    else:
        return jsonify({'error': 'Invalid MFA token'}), 401

@app.route('/api/data', methods=['POST'])
def get_data():
    # Check session
    if 'authenticated' not in session or not session['authenticated']:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Check session expiration
    if 'expires' in session:
        # Convert ISO string back to datetime
        if isinstance(session['expires'], str):
            expires_time = datetime.fromisoformat(session['expires'])
        else:
            expires_time = session['expires']
        
        # Compare naive datetimes
        if datetime.now().replace(tzinfo=None) > expires_time.replace(tzinfo=None):
            return jsonify({'error': 'Session expired'}), 401
    
    data = request.get_json()
    
    # Verify certificate
    cert = data.get('certificate')
    if not cert or not verify_certificate(cert):
        return jsonify({'error': 'Invalid certificate'}), 401
    
    # Process encrypted data
    encrypted_data = data.get('data')
    if encrypted_data:
        try:
            decrypted_data = decrypt_data(encrypted_data)
            return jsonify({
                'result': 'ok',
                'message': f'Data received and decrypted: {decrypted_data}',
                'user': session['username'],
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({'error': f'Decryption failed: {str(e)}'}), 400
    
    return jsonify({'result': 'ok', 'message': 'No data to decrypt'})

def decrypt_data(encrypted_data):
    try:
        # Load encryption key
        with open(ENCRYPTION_KEY_FILE, 'rb') as f:
            key = f.read()
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except FileNotFoundError:
        # Generate new key if not exists
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_FILE, 'wb') as f:
            f.write(key)
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except:
        # For demo, return as-is if no encryption key
        return encrypted_data

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'mfa_supported': True,
        'certificates_ready': check_certificates()
    })

if __name__ == '__main__':
    print("=== Запуск защищенного сервера с двухфакторной аутентификацией ===\n")
    
    # Создаем необходимые директории и файлы
    setup_directories()
    
    # Проверяем наличие сертификатов
    if not check_certificates():
        print("\n⚠️  ВНИМАНИЕ: Не все сертификаты найдены!")
        print("Пожалуйста, выполните следующие команды для генерации сертификатов:")
        print("\n1. Создайте корневой сертификат:")
        print(f"   openssl req -x509 -newkey rsa:4096 -keyout {CERT_DIR}/ca_key.pem -out {CERT_DIR}/ca_cert.pem -days 365 -nodes -subj '/C=RU/ST=Moscow/L=Moscow/O=DistributedSystems/CN=RootCA'")
        print("\n2. Создайте серверный сертификат:")
        print(f"   openssl req -newkey rsa:4096 -keyout {CERT_DIR}/server_key.pem -out {CERT_DIR}/server_req.pem -nodes -subj '/C=RU/ST=Moscow/L=Moscow/O=DistributedSystems/CN=server.local'")
        print(f"   openssl x509 -req -in {CERT_DIR}/server_req.pem -CA {CERT_DIR}/ca_cert.pem -CAkey {CERT_DIR}/ca_key.pem -CAcreateserial -out {CERT_DIR}/server_cert.pem -days 365")
        print("\n3. Создайте клиентский сертификат:")
        print(f"   openssl req -newkey rsa:4096 -keyout {CERT_DIR}/client_key.pem -out {CERT_DIR}/client_req.pem -nodes -subj '/C=RU/ST=Moscow/L=Moscow/O=DistributedSystems/CN=client.local'")
        print(f"   openssl x509 -req -in {CERT_DIR}/client_req.pem -CA {CERT_DIR}/ca_cert.pem -CAkey {CERT_DIR}/ca_key.pem -out {CERT_DIR}/client_cert.pem -days 365")
        print("\nИли запустите: python generate_certs.py")
        print("\nЗапускаю сервер в режиме отладки (без SSL)...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("✓ Все сертификаты найдены")
        print("✓ Ключ шифрования готов")
        
        # SSL context setup
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(SERVER_CERT, SERVER_KEY)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(CA_CERT)
            
            print(f"\n🚀 Запуск сервера на https://0.0.0.0:5000")
            print("Для тестирования используйте:")
            print("1. python client.py")
            print("2. Имя пользователя: user1")
            print("3. Пароль: password123")
            
            app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=True)
        except Exception as e:
            print(f"\n⚠️  Ошибка при настройке SSL: {e}")
            print("Запускаю сервер в HTTP режиме для отладки...")
            app.run(host='0.0.0.0', port=5000, debug=True)
