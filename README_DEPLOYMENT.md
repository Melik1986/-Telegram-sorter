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