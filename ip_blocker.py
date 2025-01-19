import hashlib
import redis

class IPBlocker:
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=1, expiration_time=300):
        """
        Initializes the IPBlocker with Redis connection parameters and expiration time.

        Args:
            redis_host (str): Hostname or IP address of the Redis server (default: 'localhost').
            redis_port (int): Port number of the Redis server (default: 6379).
            redis_db (int): Redis database index to use (default: 0).
            expiration_time (int): Expiration time for blocked IPs in seconds (default: 300).
        """
        self.redis = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        self.expiration_time = expiration_time

    def block_ip(self, ip):
        """
        Hashes the given IP address and stores it in Redis with an expiration time.

        Args:
            ip (str): IP address to be blocked.
        """
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()
        self.redis.set(ip_hash, 1, ex=self.expiration_time)

    def is_blocked(self, ip):
        """
        Checks if the given IP address is currently blocked.

        Args:
            ip (str): IP address to check.

        Returns:
            bool: True if the IP is blocked, False otherwise.
        """
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()
        return self.redis.exists(ip_hash)