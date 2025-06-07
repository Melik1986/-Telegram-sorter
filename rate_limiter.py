#!/usr/bin/env python3
"""
Rate limiting system for DevDataSorter Telegram bot.
Provides protection against spam and abuse.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter with multiple strategies."""
    
    def __init__(self, 
                 requests_per_minute: int = 10,
                 requests_per_hour: int = 100,
                 burst_limit: int = 5,
                 cooldown_minutes: int = 15):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute per user
            requests_per_hour: Max requests per hour per user
            burst_limit: Max burst requests in short time
            cooldown_minutes: Cooldown period for blocked users
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.cooldown_minutes = cooldown_minutes
        
        # User request tracking
        self.user_requests = defaultdict(deque)  # user_id -> deque of timestamps
        self.user_hourly_requests = defaultdict(deque)  # user_id -> deque of timestamps
        self.blocked_users = {}  # user_id -> block_until_timestamp
        self.warning_counts = defaultdict(int)  # user_id -> warning_count
        
        logger.info(f"Rate limiter initialized: {requests_per_minute}/min, {requests_per_hour}/hour")
    
    def is_allowed(self, user_id: int, command: str = None) -> Tuple[bool, Optional[str]]:
        """
        Check if user is allowed to make a request.
        
        Args:
            user_id: Telegram user ID
            command: Command being executed (optional)
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        current_time = time.time()
        
        # Check if user is currently blocked
        if user_id in self.blocked_users:
            if current_time < self.blocked_users[user_id]:
                remaining = int(self.blocked_users[user_id] - current_time)
                return False, f"Вы заблокированы на {remaining} секунд за превышение лимитов."
            else:
                # Unblock user
                del self.blocked_users[user_id]
                self.warning_counts[user_id] = 0
                logger.info(f"User {user_id} unblocked")
        
        # Clean old requests
        self._cleanup_old_requests(user_id, current_time)
        
        # Check burst limit (last 10 seconds)
        recent_requests = [t for t in self.user_requests[user_id] 
                          if current_time - t <= 10]
        if len(recent_requests) >= self.burst_limit:
            self._apply_penalty(user_id, "burst", current_time)
            return False, f"Слишком много запросов подряд. Подождите немного."
        
        # Check per-minute limit
        minute_requests = [t for t in self.user_requests[user_id] 
                          if current_time - t <= 60]
        if len(minute_requests) >= self.requests_per_minute:
            self._apply_penalty(user_id, "minute", current_time)
            return False, f"Превышен лимит {self.requests_per_minute} запросов в минуту."
        
        # Check per-hour limit
        hour_requests = [t for t in self.user_hourly_requests[user_id] 
                        if current_time - t <= 3600]
        if len(hour_requests) >= self.requests_per_hour:
            self._apply_penalty(user_id, "hour", current_time)
            return False, f"Превышен лимит {self.requests_per_hour} запросов в час."
        
        # Record the request
        self.user_requests[user_id].append(current_time)
        self.user_hourly_requests[user_id].append(current_time)
        
        return True, None
    
    def _cleanup_old_requests(self, user_id: int, current_time: float):
        """Remove old request timestamps."""
        # Clean minute requests (keep last 2 minutes for safety)
        while (self.user_requests[user_id] and 
               current_time - self.user_requests[user_id][0] > 120):
            self.user_requests[user_id].popleft()
        
        # Clean hour requests (keep last 2 hours for safety)
        while (self.user_hourly_requests[user_id] and 
               current_time - self.user_hourly_requests[user_id][0] > 7200):
            self.user_hourly_requests[user_id].popleft()
    
    def _apply_penalty(self, user_id: int, violation_type: str, current_time: float):
        """Apply penalty to user based on violation type."""
        self.warning_counts[user_id] += 1
        warning_count = self.warning_counts[user_id]
        
        # Progressive penalties
        if warning_count == 1:
            penalty_minutes = 1
        elif warning_count == 2:
            penalty_minutes = 5
        elif warning_count == 3:
            penalty_minutes = 15
        else:
            penalty_minutes = 60  # 1 hour for repeat offenders
        
        block_until = current_time + (penalty_minutes * 60)
        self.blocked_users[user_id] = block_until
        
        logger.warning(f"User {user_id} blocked for {penalty_minutes} minutes "
                      f"(violation: {violation_type}, warnings: {warning_count})")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get rate limiting stats for a user."""
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
    
    def reset_user(self, user_id: int):
        """Reset rate limiting for a user (admin function)."""
        if user_id in self.blocked_users:
            del self.blocked_users[user_id]
        
        self.warning_counts[user_id] = 0
        self.user_requests[user_id].clear()
        self.user_hourly_requests[user_id].clear()
        
        logger.info(f"Rate limiting reset for user {user_id}")
    
    def get_global_stats(self) -> Dict:
        """Get global rate limiting statistics."""
        current_time = time.time()
        
        active_users = len([uid for uid in self.user_requests.keys() 
                           if self.user_requests[uid]])
        blocked_users = len([uid for uid, block_time in self.blocked_users.items() 
                            if current_time < block_time])
        
        total_requests_minute = sum(
            len([t for t in requests if current_time - t <= 60])
            for requests in self.user_requests.values()
        )
        
        total_requests_hour = sum(
            len([t for t in requests if current_time - t <= 3600])
            for requests in self.user_hourly_requests.values()
        )
        
        return {
            "active_users": active_users,
            "blocked_users": blocked_users,
            "total_requests_last_minute": total_requests_minute,
            "total_requests_last_hour": total_requests_hour,
            "limits": {
                "requests_per_minute": self.requests_per_minute,
                "requests_per_hour": self.requests_per_hour,
                "burst_limit": self.burst_limit,
                "cooldown_minutes": self.cooldown_minutes
            }
        }

class CommandRateLimiter:
    """Specialized rate limiter for different command types."""
    
    def __init__(self):
        """Initialize command-specific rate limiter."""
        # Different limits for different command types
        self.command_limits = {
            'search': {'per_minute': 5, 'per_hour': 50},
            'add': {'per_minute': 3, 'per_hour': 30},
            'list': {'per_minute': 2, 'per_hour': 20},
            'help': {'per_minute': 2, 'per_hour': 10},
            'categories': {'per_minute': 2, 'per_hour': 10},
            'stats': {'per_minute': 1, 'per_hour': 5},
            'message': {'per_minute': 8, 'per_hour': 80}  # Auto-classification
        }
        
        # Track command usage per user
        self.command_usage = defaultdict(lambda: defaultdict(deque))
        
        logger.info("Command rate limiter initialized")
    
    def is_command_allowed(self, user_id: int, command: str) -> Tuple[bool, Optional[str]]:
        """Check if specific command is allowed for user."""
        current_time = time.time()
        
        # Get limits for this command
        limits = self.command_limits.get(command, {'per_minute': 10, 'per_hour': 100})
        
        # Clean old usage records
        user_command_usage = self.command_usage[user_id][command]
        while user_command_usage and current_time - user_command_usage[0] > 3600:
            user_command_usage.popleft()
        
        # Check minute limit
        minute_usage = len([t for t in user_command_usage if current_time - t <= 60])
        if minute_usage >= limits['per_minute']:
            return False, f"Превышен лимит для команды '{command}': {limits['per_minute']}/мин"
        
        # Check hour limit
        hour_usage = len(user_command_usage)
        if hour_usage >= limits['per_hour']:
            return False, f"Превышен лимит для команды '{command}': {limits['per_hour']}/час"
        
        # Record usage
        user_command_usage.append(current_time)
        
        return True, None
    
    def get_command_stats(self, user_id: int, command: str) -> Dict:
        """Get command usage stats for user."""
        current_time = time.time()
        limits = self.command_limits.get(command, {'per_minute': 10, 'per_hour': 100})
        
        user_command_usage = self.command_usage[user_id][command]
        minute_usage = len([t for t in user_command_usage if current_time - t <= 60])
        hour_usage = len([t for t in user_command_usage if current_time - t <= 3600])
        
        return {
            "command": command,
            "usage_last_minute": minute_usage,
            "usage_last_hour": hour_usage,
            "minute_limit": limits['per_minute'],
            "hour_limit": limits['per_hour'],
            "minute_remaining": max(0, limits['per_minute'] - minute_usage),
            "hour_remaining": max(0, limits['per_hour'] - hour_usage)
        }

# Global rate limiter instances
_rate_limiter = None
_command_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

def get_command_rate_limiter() -> CommandRateLimiter:
    """Get global command rate limiter instance."""
    global _command_rate_limiter
    if _command_rate_limiter is None:
        _command_rate_limiter = CommandRateLimiter()
    return _command_rate_limiter