import unittest
from rate_limiter import RateLimiter
import time

#to run test
#python -m unittest rate_limiter_test.py
class RateLimiterTest(unittest.TestCase):
    def setUp(self):
        self.rate_limiter = RateLimiter()
        self.redis = self.rate_limiter.redis
        self.redis.flushdb()

    def test_initial_permit(self):
        key = "test_key"
        self.assertFalse(self.rate_limiter.is_rate_limited(key))

    def test_rate_limiting(self):
        key = "rate_limit_key"
        for _ in range(self.rate_limiter.rate_limit + 1):
            self.rate_limiter.is_rate_limited(key)
        self.assertTrue(self.rate_limiter.is_rate_limited(key))

    def test_expiration(self):
        key = "expiration_key"
        self.rate_limiter.is_rate_limited(key)  # Initial request
        time.sleep(self.rate_limiter.period + 1)  # Wait for expiration
        self.assertFalse(self.rate_limiter.is_rate_limited(key))  # Should be allowed again

    def tearDown(self):
        self.redis.flushdb()

if __name__ == '__main__':
    unittest.main()
