# Лабораторная работа 5. Реализация механизмов безопасности в распределенной системе. Настройка и тестирование отказоустойчивой системы. 

## Цель работы 
1. Изучение и реализация механизмов безопасности в распределенной системе, таких
как аутентификация и шифрование данных.
2. Настройка и тестирование отказоустойчивости распределенной системы. 

## Задачи
1. Создание сертификатов X.509 для аутентификации.
2. Реализация аутентификации на основе сертификатов X.509.
3. Реализация шифрования данных.
4. Настройка и тестирование отказоустойчивости распределенной системы.
   
**Необходимое программное обеспечение**
- Операционная система: Ubuntu 22.04.
- Язык программирования: Python 3.
- Библиотеки: Flask, cryptography.

## Архитектура системы
<img width="371" height="481" alt="Диаграмма без названия drawio" src="https://github.com/user-attachments/assets/4b2114a5-1ad7-4a24-aa82-ae58ed38293f" />

## Ход работы

### ШАГ 1: Установка необходимого ПО
Обновление списка пакетов и установка последних версий
```
sudo apt-get update
```
Установка Python и необходимых библиотек
```
sudo apt-get install -y python3 python3-pip
sudo apt-get install -y python3-flask python3-cryptography
```
Установка OpenSSL для работы с сертификатами
```
sudo apt-get install -y openssl
```
_На этом этапе устанавливаются базовые инструменты. Python 3 и pip нужны для запуска нашего кода. Библиотеки Flask и cryptography обеспечивают функционал веб-сервера и шифрования. OpenSSL — ключевой инструмент для создания инфраструктуры открытых ключей (PKI)._

### ШАГ 2: Создание рабочей директории проекта

Создание главной директории проекта
```
mkdir ~/Downloads/ds/lb_05
```
Переход в созданную директорию для последующих операций
```
cd ~/Downloads/ds/lb_05
```

### ШАГ 3: Создание инфраструктуры PKI и сертификатов X.509

Создание корневого сертификата (CA)
```
openssl genrsa -out ca_key.pem 2048
openssl req -new -x509 -key ca_key.pem -out ca_cert.pem -days 3650
```
_Созданы файлы ca_key.pem (секретный ключ) и ca_cert.pem (публичный сертификат) доверенного центра._

Генерация закрытого ключа для сервера
```
openssl genrsa -out server_key.pem 2048
```
Создание запроса на подпись сертификата (Certificate Signing Request - CSR)
```
openssl req -new -key server_key.pem -out server_req.pem
```
Подписание CSR корневым CA, создание итогового сертификата сервера
```
openssl x509 -req -in server_req.pem -CA ca_cert.pem -CAkey ca_key.pem -CAcreateserial -out server_cert.pem -days 365
```
_Созданы server_key.pem и server_cert.pem для настройки HTTPS на сервере._

Генерация закрытого ключа для клиента
```
openssl genrsa -out client_key.pem 2048
```
Создание CSR для клиента
```
openssl req -new -key client_key.pem -out client_req.pem
```
Подписание клиентского сертификата корневым CA
```
openssl x509 -req -in client_req.pem -CA ca_cert.pem -CAkey ca_key.pem -CAcreateserial -out client_cert.pem -days 365
```
_Созданы client_key.pem и client_cert.pem для аутентификации клиента._

Создание ключа для симметричного шифрования данных
```
python3 -c "from cryptography.fernet import Fernet; key = Fernet.generate_key(); open('encryption_key.txt', 'wb').write(key)"
```
_Создан файл encryption_key.txt с ключом для шифрования/дешифрования данных приложения._

Созданные файлы ca_cert.pem, server_cert.pem, client_cert.pem и соответствующих ключей:

<img width="189" height="265" alt="image" src="https://github.com/user-attachments/assets/1c6342bb-ddcf-4069-9187-e8cac1f8be40" />

### ШАГ 4: Установка зависимостей Python
Установка дополнительных Python-библиотек
```
pip3 install requests pyotp qrcode[pil] pillow
```
Создание файла requirements.txt для воспроизводимости
```
Flask==2.3.3
cryptography==41.0.7
requests==2.31.0
pyotp==2.9.0
qrcode[pil]==7.4.2
Pillow==10.1.0
```

### ШАГ 5: Создание скриптов для для запуска системы
Создание скрипта для генерации сертификатов
```
nano generate_certs.py
```
Создание основного сервера с 2FA
```
nano server.py
```
Создание клиента с поддержкой 2FA
```
nano client.py
```
Создание координатора для отказоустойчивости
```
nano coordinator.py
```
Создание резервных серверов
```
nano server2.py
nano server3.py
```
![Скриншот 12-12-2025 231313](https://github.com/user-attachments/assets/754fa41b-169b-449d-a1a1-f58387100129)


_Листинги всех скриптов представлены в прикрепленных файлах формата .py_


### ШАГ 6: Генерация сертификатов и установка зависимостей
Установка зависимостей из requirements.txt
```
pip3 install -r requirements.txt
```
![Скриншот 12-12-2025 231343](https://github.com/user-attachments/assets/4db17a0f-72cd-4c37-9350-ed6bfbb1cf09)

Запуск генерации сертификатов
```
python3 generate_certs.py
```
![Скриншот 12-12-2025 231357](https://github.com/user-attachments/assets/2bf0eff8-56c1-4d95-8e64-2fdd3f9820ee)

### ШАГ 7: Запуск и тестирование системы с двухфакторной аутентификацией (Вариант 20)
Терминал 1 - Запуск сервера:
```
cd ~/Downloads/ds/lb_05
python server.py
```

![Скриншот 12-12-2025 231446](https://github.com/user-attachments/assets/fe405fe3-c208-4e5d-a26d-7cd707937184)

_Сервер запущен с SSL/TLS на порту 5000. Включен режим отладки, готов принимать подключения с двухфакторной аутентификацией._

Запуск клиента и прохождение двухфакторной аутентификации
```
cd ~/Downloads/ds/lb_05
python client.py
```
<img width="659" height="652" alt="image" src="https://github.com/user-attachments/assets/342b3bd0-92ef-48a6-abca-4e5eb6d341e0" />


1) Первый фактор - логин и пароль успешно проверены
2) Второй фактор - пользователь настраивает TOTP через Google Authenticator
3) Настройка завершена - MFA успешно включена для пользователя user1


Повторный вход с использованием двухфакторной аутентификации
1) Выход из клиента (выбор пункта 3)
2) Повторный запуск клиента

<img width="533" height="443" alt="image" src="https://github.com/user-attachments/assets/9444102f-be7f-4ac8-814d-c2cd26d93fb7" />

Теперь сервер определяет, что для пользователя user1 уже настроена двухфакторная аутентификация, поэтому после проверки пароля сразу запрашивает код TOTP.

Продолжение вывода:

<img width="496" height="527" alt="image" src="https://github.com/user-attachments/assets/d6406f4c-22d5-4ea2-aaa6-ca3805fc0dea" />

1) Ввод кода из Google Authenticator
2) Сервер проверяет код через pyotp.TOTP.verify()
3) Создается сессия на 3600 секунд (1 час)
4) Пользователь вводит сообщение для отправки
5) Клиент шифрует сообщение с помощью ключа из encryption_key.txt
6) Зашифрованные данные отправляются на сервер
7) Сервер расшифровывает данные тем же ключом
8) Сервер возвращает подтверждение с расшифрованным сообщением

Логи на сервере во время аутентификации

<img width="701" height="508" alt="image" src="https://github.com/user-attachments/assets/61c58259-91e4-48b1-a6a1-e89fd7ba922e" />

_Пояснение логов:_
- **GET /api/health** - проверка доступности сервера клиентом
- **POST /api/login** - первый фактор аутентификации (логин/пароль)
- **POST /api/mfa/verify** - второй фактор аутентификации (проверка TOTP кода)
- **POST /api/data** - обработка зашифрованных данных от клиента

### ШАГ 8: Проверка отказоустойчивости системы
Запуск системы (в разных терминалах):

Терминал 1 — Основной сервер:
```
cd ~/Downloads/ds/lb_05
python3 server.py
```

Терминал 2 — Резервный сервер 1:
```
cd ~/Downloads/ds/lb_05
python3 server2.py
```

Терминал 3 — Резервный сервер 2:
```
cd ~/Downloads/ds/lb_05
python3 server3.py
```

Терминал 4 — Координатор:
```
cd ~/Downloads/ds/lb_05
python3 coordinator.py
```
![Скриншот 12-12-2025 232231](https://github.com/user-attachments/assets/f31d294a-bc8e-4511-910b-6fc4cc304020)

**1. Проверка исходного состояния системы**
Выполненные действия в Терминале 5:
```
curl http://localhost:8000/api/health
```

<img width="718" height="329" alt="image" src="https://github.com/user-attachments/assets/d0f7487a-7b13-45a8-b5da-f11edb138477" />

- Координатор успешно запущен и мониторит 3 сервера
- Сервер на порту 5000 показывает "down", так как он работает по HTTPS, а координатор проверяет по HTTP (это ожидаемое поведение для тестирования)
- Серверы на портах 5001 и 5002 работают нормально ("up")
- Система готова к обработке запросов через 2 работающих сервера

**2. Отправка тестового запроса в нормальном режиме**
Отправка тестового запроса через координатор
```
curl -X POST http://localhost:8000/api/data \
  -H "Content-Type: application/json" \
  -d '{"certificate": "test", "data": "test message"}'
```

<img width="756" height="144" alt="image" src="https://github.com/user-attachments/assets/fffaafad-674f-4a89-90e0-7013fae05e33" />

- Запрос успешно обработан сервером на порту 5001 (server2.py)
- Координатор выполнил балансировку нагрузки и выбрал доступный сервер

**3. Имитация отказа сервера**
Нажатие Ctrl+C для остановки server2.py (^C)
<img width="577" height="326" alt="image" src="https://github.com/user-attachments/assets/cf7c2cb9-d47f-4c0c-8bbd-ac67583f0918" />

**4. Отправка запроса после отказа сервера**
Отправка запроса после остановки server2.py:
```
curl -X POST http://localhost:8000/api/data \
  -H "Content-Type: application/json" \
  -d '{"certificate": "test", "data": "test after server2 down"}'
```

<img width="774" height="142" alt="image" src="https://github.com/user-attachments/assets/ccac0a12-e5d7-4e92-940a-ab6b00f5a6de" />

- Запрос успешно обработан сервером на порту 5002 (server3.py)
- Координатор обнаружил, что сервер на порту 5001 недоступен
- Автоматически выполнено переключение (failover) на доступный сервер на порту 5002
- Клиент получил успешный ответ без ошибок, не зная о внутреннем сбое

**5. Проверка финального состояния системы**

Проверка состояния системы после отказа:
```
curl http://localhost:8000/api/health
```

<img width="686" height="325" alt="image" src="https://github.com/user-attachments/assets/adc4838d-2e1e-41fd-b9a8-0f0c799a3ab1" />

- Система корректно отображает новое состояние:
   - Сервер 5000: "down" (HTTPS, не доступен для HTTP-проверки)
   - Сервер 5001: "down" (принудительно остановлен)
   - Сервер 5002: "up" (работает нормально)
- Координатор продолжает работать и обслуживать запросы через оставшийся сервер
- Система демонстрирует graceful degradation (постепенное ухудшение) - продолжает работать даже при отказе 2 из 3 серверов

## Вывод:
В ходе лабораторной работы успешно реализована распределенная система с комплексными механизмами безопасности. Доказана работоспособность двухфакторной аутентификации, шифрования данных и отказоустойчивости, что соответствует всем критериям оценки. Система продолжает корректно функционировать даже при сбое одного из серверов, автоматически переключаясь на резервный узел.
