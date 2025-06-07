#!/bin/bash

# Скрипт для настройки Oracle Cloud Always Free VPS для DevDataSorter

set -e

echo "🚀 Настройка Oracle Cloud VPS для DevDataSorter..."

# Обновление системы
echo "📦 Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Установка Docker
echo "🐳 Установка Docker..."
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
echo "🔧 Установка Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Создание директорий для проекта
echo "📁 Создание директорий..."
mkdir -p /home/ubuntu/devdatasorter/{cache,logs}

# Настройка файрвола (открытие портов)
echo "🔥 Настройка файрвола..."
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

# Создание systemd сервиса для автозапуска
echo "⚙️ Создание systemd сервиса..."
sudo tee /etc/systemd/system/devdatasorter.service > /dev/null <<EOF
[Unit]
Description=DevDataSorter Telegram Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker run -d \
  --name devdatasorter-bot \
  --restart unless-stopped \
  -v /home/ubuntu/devdatasorter/cache:/app/src/utils/cache \
  -v /home/ubuntu/devdatasorter/logs:/app/logs \
  -p 8000:8000 \
  devdatasorter:latest
ExecStop=/usr/bin/docker stop devdatasorter-bot
ExecStopPost=/usr/bin/docker rm devdatasorter-bot

[Install]
WantedBy=multi-user.target
EOF

# Включение сервиса
sudo systemctl daemon-reload
sudo systemctl enable devdatasorter.service

echo "✅ Настройка завершена!"
echo "📋 Следующие шаги:"
echo "1. Перезагрузите систему: sudo reboot"
echo "2. Настройте переменные окружения в GitHub Secrets"
echo "3. Запустите GitHub Actions для развертывания"
echo "4. Проверьте статус: docker ps"
echo "5. Просмотр логов: docker logs devdatasorter-bot"

echo "🌐 Веб-интерфейс будет доступен по адресу: http://YOUR_ORACLE_IP:8000"