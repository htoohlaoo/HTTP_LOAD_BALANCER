import redis
import time
import hashlib

class RateLimiter:
    def __init__(self, redis_host='localhost', redis_port=6379, db=0, rate_limit=50, period=60):
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=db)
        self.rate_limit = rate_limit
        self.period = period

    def hash_key(self, key):
        return hashlib.sha256(key.encode()).hexdigest()

    def is_rate_limited(self, key):
        hashed_key = self.hash_key(key)

        # Check if the key exists and get its current count
        current_count = self.redis.hincrby(hashed_key, 'count')
        print(key,'/ Count :',current_count)
        # If this is the first request for this key, set an expiration
        if current_count == 1:
            self.redis.expire(hashed_key, self.period)

        return current_count > self.rate_limit
    
    def clear_rate_limiter(self):
        self.redis.flushdb()

