# 🚀 Развертывание DevDataSorter на Oracle Cloud Always Free

Это руководство поможет вам развернуть Telegram бота DevDataSorter на **полностью бесплатной** платформе Oracle Cloud Always Free.

## 🎯 Почему Oracle Cloud Always Free?

- ✅ **Полностью бесплатно навсегда** (не пробный период)
- ✅ **2 VM инстанса** с 1 GB RAM каждый
- ✅ **200 GB блочного хранилища**
- ✅ **10 TB исходящего трафика в месяц**
- ✅ **Без ограничений по времени работы**
- ✅ **ARM процессоры** (более эффективные)

## 📋 Предварительные требования

1. Аккаунт Oracle Cloud (бесплатная регистрация)
2. Аккаунт GitHub
3. Аккаунт Docker Hub (бесплатный)
4. Telegram Bot Token от @BotFather

## 🔧 Пошаговая инструкция

### Шаг 1: Создание Oracle Cloud аккаунта

1. Перейдите на [Oracle Cloud](https://www.oracle.com/cloud/free/)
2. Нажмите "Start for free"
3. Заполните форму регистрации
4. Подтвердите email и телефон
5. Добавьте кредитную карту (для верификации, списаний не будет)

### Шаг 2: Создание VM инстанса

1. Войдите в Oracle Cloud Console
2. Перейдите в **Compute** → **Instances**
3. Нажмите **Create Instance**
4. Настройте инстанс:
   - **Name**: `devdatasorter-bot`
   - **Image**: `Ubuntu 22.04`
   - **Shape**: `VM.Standard.A1.Flex` (ARM, бесплатный)
   - **OCPU**: `1`
   - **Memory**: `6 GB` (максимум для бесплатного)
   - **Boot Volume**: `50 GB`

5. В разделе **Networking**:
   - Создайте новую VCN или используйте существующую
   - Убедитесь, что **Assign public IP** включено

6. В разделе **Add SSH keys**:
   - Сгенерируйте новую пару ключей или загрузите существующий публичный ключ
   - **Сохраните приватный ключ!**

7. Нажмите **Create**

### Шаг 3: Настройка Security List

1. Перейдите в **Networking** → **Virtual Cloud Networks**
2. Выберите вашу VCN
3. Перейдите в **Security Lists**
4. Выберите Default Security List
5. Нажмите **Add Ingress Rules**
6. Добавьте правило:
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: `TCP`
   - **Destination Port Range**: `8000`
   - **Description**: `DevDataSorter Web Interface`

### Шаг 4: Подключение к серверу

```bash
# Замените YOUR_PRIVATE_KEY.pem и YOUR_PUBLIC_IP
ssh -i YOUR_PRIVATE_KEY.pem ubuntu@YOUR_PUBLIC_IP
```

### Шаг 5: Настройка сервера

1. Скопируйте и выполните скрипт настройки:

```bash
# Скачать скрипт настройки
wget https://raw.githubusercontent.com/YOUR_USERNAME/DevDataSorter/main/scripts/setup_oracle_cloud.sh

# Сделать исполняемым
chmod +x setup_oracle_cloud.sh

# Выполнить
./setup_oracle_cloud.sh

# Перезагрузить систему
sudo reboot
```

### Шаг 6: Настройка GitHub Secrets

1. Перейдите в ваш GitHub репозиторий
2. **Settings** → **Secrets and variables** → **Actions**
3. Добавьте следующие secrets:

```
DOCKER_USERNAME=your_dockerhub_username
DOCKER_PASSWORD=your_dockerhub_password
ORACLE_HOST=your_oracle_public_ip
ORACLE_USERNAME=ubuntu
ORACLE_SSH_KEY=your_private_ssh_key_content
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
OLLAMA_BASE_URL=http://localhost:11434
ADMIN_USER_ID=your_telegram_user_id
```

### Шаг 7: Развертывание

1. Сделайте commit и push в main ветку
2. GitHub Actions автоматически:
   - Соберет Docker образ
   - Загрузит его в Docker Hub
   - Развернет на Oracle Cloud

### Шаг 8: Проверка

```bash
# Подключиться к серверу
ssh -i YOUR_PRIVATE_KEY.pem ubuntu@YOUR_PUBLIC_IP

# Проверить статус контейнера
docker ps

# Просмотреть логи
docker logs devdatasorter-bot

# Проверить веб-интерфейс
curl http://localhost:8000/health
```

## 🌐 Доступ к боту

- **Telegram бот**: Найдите вашего бота в Telegram
- **Веб-интерфейс**: `http://YOUR_ORACLE_IP:8000`
- **Мониторинг**: `http://YOUR_ORACLE_IP:8000/health`

## 🔧 Управление

### Обновление бота

```bash
# Автоматически через GitHub Actions при push в main
git add .
git commit -m "Update bot"
git push origin main
```

### Ручное управление

```bash
# Остановить бота
docker stop devdatasorter-bot

# Запустить бота
docker start devdatasorter-bot

# Перезапустить бота
docker restart devdatasorter-bot

# Просмотр логов в реальном времени
docker logs -f devdatasorter-bot
```

### Мониторинг ресурсов

```bash
# Использование CPU и памяти
docker stats devdatasorter-bot

# Использование диска
df -h

# Системная информация
htop
```

## 🛠️ Альтернативные бесплатные платформы

Если Oracle Cloud недоступен:

### 1. Railway (500 часов/месяц)
```bash
# Установить Railway CLI
npm install -g @railway/cli

# Войти в аккаунт
railway login

# Развернуть
railway up
```

### 2. Render (спит после 15 минут бездействия)
1. Подключите GitHub репозиторий
2. Выберите "Web Service"
3. Настройте переменные окружения
4. Развертывание автоматическое

### 3. Fly.io (бесплатный уровень)
```bash
# Установить flyctl
curl -L https://fly.io/install.sh | sh

# Войти в аккаунт
fly auth login

# Развернуть
fly deploy
```

## 🆘 Устранение неполадок

### Проблема: Не удается создать ARM инстанс
**Решение**: Попробуйте разные регионы или используйте скрипт автоматического создания:

```bash
# Скрипт для автоматического создания ARM инстанса
wget https://raw.githubusercontent.com/hitrov/oci-arm-host-capacity/master/oci-arm-host-capacity.py
python3 oci-arm-host-capacity.py
```

### Проблема: Бот не отвечает
```bash
# Проверить логи
docker logs devdatasorter-bot

# Проверить переменные окружения
docker exec devdatasorter-bot env | grep TELEGRAM

# Перезапустить
docker restart devdatasorter-bot
```

### Проблема: Недостаточно памяти
```bash
# Проверить использование памяти
free -h
docker stats

# Очистить неиспользуемые образы
docker system prune -f
```

## 📊 Мониторинг и логирование

### Настройка логирования

```bash
# Настроить ротацию логов
sudo tee /etc/logrotate.d/docker > /dev/null <<EOF
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  size=1M
  missingok
  delaycompress
  copytruncate
}
EOF
```

### Мониторинг с помощью cron

```bash
# Добавить в crontab
crontab -e

# Добавить строку для проверки каждые 5 минут
*/5 * * * * docker ps | grep devdatasorter-bot || docker start devdatasorter-bot
```

## 🎉 Готово!

Ваш Telegram бот DevDataSorter теперь работает **24/7 абсолютно бесплатно** на Oracle Cloud Always Free!

### Полезные ссылки:
- [Oracle Cloud Console](https://cloud.oracle.com/)
- [Docker Hub](https://hub.docker.com/)
- [GitHub Actions](https://github.com/features/actions)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

**💡 Совет**: Сохраните все ключи и пароли в безопасном месте. Регулярно проверяйте логи и мониторьте использование ресурсов.