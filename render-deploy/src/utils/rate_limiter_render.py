"""
Система ограничения запросов для Render.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class RateLimiter:
    """Ограничитель запросов для защиты от спама."""
    
    def __init__(self, 
                 requests_per_minute: int = 15,
                 requests_per_hour: int = 150,
                 burst_limit: int = 8):
        """
        Инициализация ограничителя запросов.
        
        Args:
            requests_per_minute: Максимум запросов в минуту на пользователя
            requests_per_hour: Максимум запросов в час на пользователя
            burst_limit: Максимум быстрых запросов подряд
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # Отслеживание запросов пользователей
        self.user_requests = defaultdict(deque)
        self.user_hourly_requests = defaultdict(deque)
        self.blocked_users = {}
        self.warning_counts = defaultdict(int)
        
        logger.info(f"Rate limiter initialized: {requests_per_minute}/min, {requests_per_hour}/hour")
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Проверить, разрешен ли запрос пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            True если запрос разрешен, False если заблокирован
        """
        current_time = time.time()
        
        # Проверить, заблокирован ли пользователь
        if user_id in self.blocked_users:
            if current_time < self.blocked_users[user_id]:
                return False
            else:
                # Разблокировать пользователя
                del self.blocked_users[user_id]
                self.warning_counts[user_id] = 0
                logger.info(f"User {user_id} unblocked")
        
        # Очистить старые запросы
        self._cleanup_old_requests(user_id, current_time)
        
        # Проверить лимит быстрых запросов (последние 10 секунд)
        recent_requests = [t for t in self.user_requests[user_id] 
                          if current_time - t <= 10]
        if len(recent_requests) >= self.burst_limit:
            self._apply_penalty(user_id, "burst", current_time)
            return False
        
        # Проверить лимит в минуту
        minute_requests = [t for t in self.user_requests[user_id] 
                          if current_time - t <= 60]
        if len(minute_requests) >= self.requests_per_minute:
            self._apply_penalty(user_id, "minute", current_time)
            return False
        
        # Проверить лимит в час
        hour_requests = [t for t in self.user_hourly_requests[user_id] 
                        if current_time - t <= 3600]
        if len(hour_requests) >= self.requests_per_hour:
            self._apply_penalty(user_id, "hour", current_time)
            return False
        
        # Записать запрос
        self.user_requests[user_id].append(current_time)
        self.user_hourly_requests[user_id].append(current_time)
        
        return True
    
    def _cleanup_old_requests(self, user_id: int, current_time: float):
        """Удалить старые записи запросов."""
        # Очистить минутные запросы (оставить последние 2 минуты для безопасности)
        while (self.user_requests[user_id] and 
               current_time - self.user_requests[user_id][0] > 120):
            self.user_requests[user_id].popleft()
        
        # Очистить часовые запросы (оставить последние 2 часа для безопасности)
        while (self.user_hourly_requests[user_id] and 
               current_time - self.user_hourly_requests[user_id][0] > 7200):
            self.user_hourly_requests[user_id].popleft()
    
    def _apply_penalty(self, user_id: int, violation_type: str, current_time: float):
        """Применить штраф к пользователю."""
        self.warning_counts[user_id] += 1
        warning_count = self.warning_counts[user_id]
        
        # Прогрессивные штрафы
        if warning_count == 1:
            penalty_minutes = 2
        elif warning_count == 2:
            penalty_minutes = 10
        else:
            penalty_minutes = 30
        
        block_until = current_time + (penalty_minutes * 60)
        self.blocked_users[user_id] = block_until
        
        logger.warning(f"User {user_id} blocked for {penalty_minutes} minutes "
                      f"(violation: {violation_type}, warnings: {warning_count})")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику ограничений для пользователя."""
        current_time = time.time()
        self._cleanup_old_requests(user_id, current_time)
        
        minute_requests = len([t for t in self.user_requests[user_id] 
                              if current_time - t <= 60])
        hour_requests = len([t for t in self.user_hourly_requests[user_id] 
                            if current_time - t <= 3600])
        
        is_blocked = user_id in self.blocked_users and current_time < self.blocked_users[user_id]
        block_remaining = 0
        if is_blocked:
            block_remaining = int(self.blocked_users[user_id] - current_time)
        
        return {
            "user_id": user_id,
            "requests_last_minute": minute_requests,
            "requests_last_hour": hour_requests,
            "minute_limit": self.requests_per_minute,
            "hour_limit": self.requests_per_hour,
            "is_blocked": is_blocked,
            "block_remaining_seconds": block_remaining,
            "warning_count": self.warning_counts[user_id],
            "minute_remaining": max(0, self.requests_per_minute - minute_requests),
            "hour_remaining": max(0, self.requests_per_hour - hour_requests)
        }