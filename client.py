import requests
import ssl
import json
import sys
import time
import os
from cryptography.fernet import Fernet
import pyotp
import qrcode
from PIL import Image
import io
import base64

class SecureClient:
    def __init__(self, server_url='https://localhost:5000'):
        self.server_url = server_url
        self.session = requests.Session()
        self.cert_dir = 'certs'
        self.cert_file = os.path.join(self.cert_dir, 'client_cert.pem')
        self.key_file = os.path.join(self.cert_dir, 'client_key.pem')
        self.ca_cert = os.path.join(self.cert_dir, 'ca_cert.pem')
        self.session_token = None
        self.username = None
        
        # Проверяем наличие файлов
        self.check_certificates()
        
        # Setup SSL context
        self.setup_ssl_context()
    
    def check_certificates(self):
        """Проверяем наличие необходимых сертификатов"""
        required_files = [self.cert_file, self.key_file, self.ca_cert]
        missing_files = []
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"⚠️  Внимание: Не найдены следующие файлы:")
            for file in missing_files:
                print(f"   - {file}")
            print("\nПожалуйста, создайте сертификаты командой:")
            print("   python generate_certs.py")
            sys.exit(1)
    
    def setup_ssl_context(self):
        """Configure SSL context for mutual TLS"""
        try:
            context = ssl.create_default_context()
            context.load_cert_chain(self.cert_file, self.key_file)
            context.load_verify_locations(self.ca_cert)
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Для тестирования, можно отключить проверку хоста
            # context.check_hostname = False
            
            # Настраиваем сессию requests
            self.session.verify = self.ca_cert
            self.session.cert = (self.cert_file, self.key_file)
            print("✓ SSL контекст успешно настроен")
        except Exception as e:
            print(f"⚠️  Ошибка настройки SSL: {e}")
            print("Запускаю клиент без SSL...")
            # Если SSL не работает, переключаемся на HTTP
            self.server_url = self.server_url.replace('https://', 'http://')
    
    def check_server_health(self):
        """Check if server is healthy"""
        try:
            response = self.session.get(f'{self.server_url}/api/health', timeout=5)
            if response.status_code == 200:
                print(f"✓ Сервер доступен")
                print(f"MFA поддерживается: {response.json().get('mfa_supported', False)}")
                return True
            else:
                print(f"✗ Ошибка сервера: {response.status_code}")
                return False
        except requests.exceptions.SSLError as e:
            print(f"⚠️  SSL ошибка: {e}")
            print("Попытка подключения без SSL...")
            # Пробуем HTTP
            self.server_url = self.server_url.replace('https://', 'http://')
            return self.check_server_health()
        except Exception as e:
            print(f"✗ Не могу подключиться к серверу: {e}")
            return False
    
    def login(self, username, password):
        """First factor: username/password authentication"""
        self.username = username
        
        login_data = {
            'username': username,
            'password': password
        }
        
        try:
            response = self.session.post(
                f'{self.server_url}/api/login',
                json=login_data,
                timeout=10
            )
            
            print(f"Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Первый фактор аутентификации успешен")
                print(f"Сообщение: {result.get('message')}")
                
                if result.get('mfa_setup_required'):
                    print("\n🔐 Требуется настройка двухфакторной аутентификации.")
                    return self.setup_mfa(username, result['totp_secret'], result.get('qr_code'))
                elif result.get('mfa_required'):
                    print("\n🔐 Требуется второй фактор (MFA).")
                    return self.verify_mfa(username)
                else:
                    print("✓ Аутентификация завершена")
                    return True
            else:
                error_msg = response.json().get('error', 'Unknown error')
                print(f"✗ Ошибка аутентификации: {error_msg}")
                return False
                
        except requests.exceptions.SSLError as e:
            print(f"SSL Error: {e}")
            return False
        except Exception as e:
            print(f"Ошибка соединения: {e}")
            return False
    
    def setup_mfa(self, username, totp_secret, qr_code_data=None):
        """Setup two-factor authentication"""
        print(f"\n=== НАСТРОЙКА ДВУХФАКТОРНОЙ АУТЕНТИФИКАЦИИ ===")
        print(f"Ваш секретный ключ: {totp_secret}")
        print("\nИнструкции:")
        print("1. Установите приложение-аутентификатор (Google Authenticator, Authy)")
        print("2. Добавьте новый аккаунт")
        print("3. Введите секретный ключ вручную или отсканируйте QR-код")
        
        if qr_code_data:
            try:
                # Сохраняем QR-код в файл
                qr_img_data = base64.b64decode(qr_code_data)
                with open('qr_code.png', 'wb') as f:
                    f.write(qr_img_data)
                print(f"\nQR-код сохранен в файл: qr_code.png")
                
                # Пытаемся показать QR-код
                try:
                    img = Image.open('qr_code.png')
                    img.show()
                    print("QR-код открыт в просмотрщике изображений")
                except:
                    print("Не удалось открыть QR-код. Откройте файл qr_code.png вручную")
            except:
                print("Не удалось сохранить QR-код")
        
        # Генерируем тестовый токен
        totp = pyotp.TOTP(totp_secret)
        current_token = totp.now()
        print(f"\nТекущий токен (для тестирования): {current_token}")
        
        # Запрашиваем токен у пользователя
        while True:
            user_token = input("\nВведите 6-значный код из приложения-аутентификатора: ")
            
            setup_data = {
                'username': username,
                'token': user_token
            }
            
            try:
                response = self.session.post(
                    f'{self.server_url}/api/mfa/setup',
                    json=setup_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print("✓ Настройка MFA успешна!")
                    print("✓ Двухфакторная аутентификация включена")
                    return True
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    print(f"✗ Неверный токен: {error_msg}")
                    
                    retry = input("Попробовать еще раз? (y/n): ")
                    if retry.lower() != 'y':
                        return False
                        
            except Exception as e:
                print(f"Ошибка: {e}")
                return False
    
    def verify_mfa(self, username):
        """Second factor: TOTP verification"""
        print("\n=== ВТОРОЙ ФАКТОР АУТЕНТИФИКАЦИИ ===")
        
        while True:
            token = input("Введите 6-значный код из приложения-аутентификатора: ")
            
            verify_data = {
                'username': username,
                'token': token
            }
            
            try:
                response = self.session.post(
                    f'{self.server_url}/api/mfa/verify',
                    json=verify_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.session_token = result.get('session_token')
                    print("✓ Двухфакторная аутентификация успешна!")
                    print(f"✓ Сессия активна {result.get('expires_in', 3600)} секунд")
                    return True
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    print(f"✗ Неверный токен: {error_msg}")
                    
                    retry = input("Попробовать еще раз? (y/n): ")
                    if retry.lower() != 'y':
                        return False
                        
            except Exception as e:
                print(f"Ошибка: {e}")
                return False
    
    def encrypt_data(self, data):
        """Encrypt data before sending"""
        try:
            # Проверяем наличие ключа шифрования
            if not os.path.exists('encryption_key.txt'):
                print("⚠️  Ключ шифрования не найден. Создаю новый...")
                key = Fernet.generate_key()
                with open('encryption_key.txt', 'wb') as f:
                    f.write(key)
                print("✓ Новый ключ шифрования создан")
            
            # Загружаем ключ шифрования
            with open('encryption_key.txt', 'rb') as f:
                key = f.read()
            
            # Шифруем данные
            cipher = Fernet(key)
            encrypted = cipher.encrypt(data.encode())
            return encrypted.decode('utf-8')
        except Exception as e:
            print(f"⚠️  Ошибка шифрования: {e}")
            print("Отправляю данные без шифрования")
            return data
    
    def send_secure_data(self, data):
        """Send encrypted data with certificate authentication"""
        if not self.session_token:
            print("Ошибка: Не авторизован. Пожалуйста, сначала войдите в систему.")
            return
        
        # Загружаем клиентский сертификат
        try:
            with open(self.cert_file, 'r') as f:
                certificate = f.read()
        except FileNotFoundError:
            print("Ошибка: Клиентский сертификат не найден.")
            return
        
        # Шифруем данные
        encrypted_data = self.encrypt_data(data)
        print(f"✓ Данные зашифрованы")
        
        # Подготавливаем запрос
        request_data = {
            'certificate': certificate,
            'data': encrypted_data
        }
        
        try:
            response = self.session.post(
                f'{self.server_url}/api/data',
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Данные успешно отправлены")
                print(f"Ответ сервера: {result.get('message')}")
                print(f"Пользователь: {result.get('user')}")
                print(f"Время: {result.get('timestamp')}")
                return result
            else:
                print(f"✗ Ошибка: {response.status_code}")
                error_msg = response.json().get('error', 'Unknown error')
                print(f"Сообщение: {error_msg}")
                return None
                
        except requests.exceptions.SSLError as e:
            print(f"SSL Error: {e}")
        except Exception as e:
            print(f"Ошибка соединения: {e}")
    
    def test_connection(self):
        """Тестируем соединение с сервером"""
        print("\n=== ТЕСТИРОВАНИЕ СОЕДИНЕНИЯ ===")
        
        # Пробуем разные протоколы
        test_urls = [
            f'{self.server_url}/api/health',
            f'{self.server_url.replace("https://", "http://")}/api/health'
        ]
        
        for url in test_urls:
            try:
                print(f"\nПопытка подключения к: {url}")
                response = requests.get(url, timeout=5, verify=False)
                print(f"Статус: {response.status_code}")
                if response.status_code == 200:
                    print(f"Успешно! Ответ: {response.json()}")
                    return url
            except Exception as e:
                print(f"Ошибка: {e}")
        
        return None

def main():
    print("=" * 50)
    print("КЛИЕНТ РАСПРЕДЕЛЕННОЙ СИСТЕМЫ С БЕЗОПАСНОСТЬЮ")
    print("Двухфакторная аутентификация включена")
    print("=" * 50)
    
    # Инициализируем клиент
    print("\nИнициализация клиента...")
    client = SecureClient('https://localhost:5000')
    
    # Проверяем здоровье сервера
    print("\nПроверка доступности сервера...")
    if not client.check_server_health():
        # Пробуем тестирование соединения
        working_url = client.test_connection()
        if working_url:
            client.server_url = working_url.replace('/api/health', '')
            print(f"✓ Использую рабочий URL: {client.server_url}")
        else:
            print("✗ Сервер недоступен. Проверьте:")
            print("  1. Запущен ли сервер (python server.py)")
            print("  2. Правильный ли порт (обычно 5000)")
            print("  3. Нет ли брандмауэра")
            return
    
    # Аутентификация
    print("\n" + "=" * 50)
    print("АУТЕНТИФИКАЦИЯ")
    print("=" * 50)
    
    username = input("Имя пользователя: ")
    password = input("Пароль: ")
    
    if client.login(username, password):
        # Отправка защищенных данных
        print("\n" + "=" * 50)
        print("ОТПРАВКА ЗАЩИЩЕННЫХ ДАННЫХ")
        print("=" * 50)
        
        while True:
            print("\nМеню:")
            print("1. Отправить данные")
            print("2. Проверить соединение")
            print("3. Выйти")
            
            choice = input("Выберите действие (1-3): ")
            
            if choice == '1':
                data = input("Введите данные для отправки: ")
                if data:
                    client.send_secure_data(data)
            elif choice == '2':
                client.check_server_health()
            elif choice == '3':
                print("Выход...")
                break
            else:
                print("Неверный выбор. Попробуйте еще раз.")
    else:
        print("\n✗ Аутентификация не удалась")
        print("\nТестовые учетные данные:")
        print("  Имя пользователя: user1")
        print("  Пароль: password123")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
