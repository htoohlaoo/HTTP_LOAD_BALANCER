import time
import collections

class RateLimiter:
    def __init__(self, request_limit, time_window):
        """
        Initializes the rate limiter with a request limit and a time window.
        
        Args:
            request_limit (int): The maximum number of allowed requests within the time window.
            time_window (int): The time window in seconds for the rate limit.
        """
        self.request_limit = request_limit
        self.time_window = time_window
        self.requests = collections.defaultdict(list)

    def record_request(self, ip_address):
        now = time.time()
        self.requests[ip_address].append(now)
        # Remove old requests outside the time window
        self.requests[ip_address] = [timestamp for timestamp in self.requests[ip_address] if now - timestamp < self.time_window]

    def is_rate_limited(self, ip_address):
        """
        Checks if an IP address is rate-limited.
        """
        self.record_request(ip_address)  # Record the current request
        if len(self.requests[ip_address]) > self.request_limit:
            return True
        return False
