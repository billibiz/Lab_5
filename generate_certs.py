import subprocess
import os

def generate_certificates():
    """Generate all necessary certificates"""
    
    # Create directory for certificates
    cert_dir = 'certs'
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
        print(f"📁 Создана директория: {cert_dir}")
    
    print("🔐 Генерация корневого сертификата CA...")
    # Generate CA certificate
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
        '-keyout', f'{cert_dir}/ca_key.pem',
        '-out', f'{cert_dir}/ca_cert.pem',
        '-days', '365', '-nodes',
        '-subj', '/C=RU/ST=Moscow/L=Moscow/O=DistributedSystems/CN=RootCA'
    ], check=True)
    
    print("\n�� Генерация серверного сертификата...")
    # Generate server certificate
    subprocess.run([
        'openssl', 'req', '-newkey', 'rsa:4096',
        '-keyout', f'{cert_dir}/server_key.pem',
        '-out', f'{cert_dir}/server_req.pem',
        '-nodes',
        '-subj', '/C=RU/ST=Moscow/L=Moscow/O=DistributedSystems/CN=server.local'
    ], check=True)
    
    subprocess.run([
        'openssl', 'x509', '-req',
        '-in', f'{cert_dir}/server_req.pem',
        '-CA', f'{cert_dir}/ca_cert.pem',
        '-CAkey', f'{cert_dir}/ca_key.pem',
        '-CAcreateserial',
        '-out', f'{cert_dir}/server_cert.pem',
        '-days', '365'
    ], check=True)
    
    print("\n🔐 Генерация клиентского сертификата...")
    # Generate client certificate
    subprocess.run([
        'openssl', 'req', '-newkey', 'rsa:4096',
        '-keyout', f'{cert_dir}/client_key.pem',
        '-out', f'{cert_dir}/client_req.pem',
        '-nodes',
        '-subj', '/C=RU/ST=Moscow/L=Moscow/O=DistributedSystems/CN=client.local'
    ], check=True)
    
    subprocess.run([
        'openssl', 'x509', '-req',
        '-in', f'{cert_dir}/client_req.pem',
        '-CA', f'{cert_dir}/ca_cert.pem',
        '-CAkey', f'{cert_dir}/ca_key.pem',
        '-out', f'{cert_dir}/client_cert.pem',
        '-days', '365'
    ], check=True)
    
    # Clean up temporary files
    temp_files = [f'{cert_dir}/server_req.pem', f'{cert_dir}/client_req.pem']
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    print("\n✅ Все сертификаты успешно сгенерированы!")
    print("📁 Файлы созданы в директории 'certs/':")
    print(f"   ├── ca_cert.pem")
    print(f"   ├── ca_key.pem")
    print(f"   ├── server_cert.pem")
    print(f"   ├── server_key.pem")
    print(f"   ├── client_cert.pem")
    print(f"   └── client_key.pem")

if __name__ == '__main__':
    print("=== Генерация SSL/TLS сертификатов для распределенной системы ===\n")
    generate_certificates()

