from rate_limiter import RateLimiter

rate_limiter = RateLimiter()

for i in range(15):
    rate_limiter.is_permitted('localhst')