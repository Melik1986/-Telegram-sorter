# 🚀 Быстрое развертывание DevDataSorter

## 🎯 Лучшее бесплатное решение: Oracle Cloud Always Free

**Oracle Cloud Always Free** - это единственная платформа, которая предоставляет:
- ✅ **Полностью бесплатно навсегда** (не пробный период)
- ✅ **24/7 работа без ограничений**
- ✅ **2 VM инстанса** с достаточными ресурсами
- ✅ **Автоматическое развертывание** через GitHub Actions

## ⚡ Быстрый старт (5 минут)

### 1. Подготовка
```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/DevDataSorter.git
cd DevDataSorter

# Скопировать пример переменных окружения
cp .env.example .env

# Отредактировать .env файл
nano .env
```

### 2. Локальное тестирование
```bash
# Запустить с Docker Compose
docker-compose up -d

# Проверить логи
docker-compose logs -f

# Остановить
docker-compose down
```

### 3. Развертывание на Oracle Cloud

1. **Создать Oracle Cloud аккаунт** (бесплатно)
2. **Создать VM инстанс** (ARM, 6GB RAM, бесплатно)
3. **Настроить GitHub Secrets**:
   - `ORACLE_HOST` - IP адрес сервера
   - `ORACLE_SSH_KEY` - приватный SSH ключ
   - `TELEGRAM_BOT_TOKEN` - токен бота
   - `DOCKER_USERNAME` - логин Docker Hub
   - `DOCKER_PASSWORD` - пароль Docker Hub

4. **Push в main ветку** - автоматическое развертывание!

## 📋 Полная инструкция

См. [DEPLOYMENT.md](./DEPLOYMENT.md) для подробного руководства.

## 🔄 Альтернативные платформы

| Платформа | Бесплатный лимит | Ограничения |
|-----------|------------------|-------------|
| **Oracle Cloud** | ♾️ Навсегда | Нет |
| Railway | 500 часов/месяц | Спит после лимита |
| Render | ♾️ | Спит после 15 мин |
| Fly.io | 160 часов/месяц | Ограниченные ресурсы |

### 🚂 Альтернативные варианты:

#### Railway

**Railway** - отличная альтернатива для быстрого развертывания с простым интерфейсом:

**Преимущества:**
- ✅ **500 часов бесплатно** в месяц
- ✅ **Простое развертывание** из GitHub
- ✅ **Автоматические SSL сертификаты**
- ✅ **Встроенная база данных** (PostgreSQL)
- ✅ **Мониторинг и логи** из коробки
- ✅ **Переменные окружения** через веб-интерфейс

**Ограничения:**
- ⚠️ **Спит после 500 часов** в месяц
- ⚠️ **Требует кредитную карту** для верификации

**Быстрое развертывание на Railway:**

1. **Регистрация:**
   ```bash
   # Установить Railway CLI
   npm install -g @railway/cli
   
   # Войти в аккаунт
   railway login
   ```

2. **Развертывание:**
   ```bash
   # В корне проекта
   railway up
   
   # Или через веб-интерфейс
   # 1. Подключить GitHub репозиторий
   # 2. Выбрать ветку main
   # 3. Railway автоматически определит Dockerfile
   ```

3. **Настройка переменных:**
   ```bash
   # Через CLI
   railway variables set TELEGRAM_BOT_TOKEN=your_token
   railway variables set OPENAI_API_KEY=your_key
   
   # Или через веб-интерфейс Railway
   ```

4. **Мониторинг:**
   - Логи: `railway logs`
   - Метрики: веб-интерфейс Railway
   - Статус: `railway status`

**Создание railway.json:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "python main.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Автоматическое развертывание:**
- Каждый push в main ветку автоматически разворачивается
- Откат к предыдущей версии одним кликом
- Превью развертывания для pull requests

## 🛠️ Команды управления

```bash
# Проверить статус
ssh ubuntu@YOUR_IP "docker ps"

# Просмотр логов
ssh ubuntu@YOUR_IP "docker logs devdatasorter-bot"

# Перезапуск
ssh ubuntu@YOUR_IP "docker restart devdatasorter-bot"

# Обновление (автоматически при git push)
git push origin main
```

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте [DEPLOYMENT.md](./DEPLOYMENT.md)
2. Посмотрите логи: `docker logs devdatasorter-bot`
3. Создайте Issue в GitHub

---

**🎉 Результат**: Ваш бот работает 24/7 абсолютно бесплатно!