import redis
import time
import json

class RateLimiter:
    def __init__(self, redis_client=redis.Redis(host='localhost', port=6379, db=0), limit=10, period=10):
        self.redis = redis_client
        self.limit = limit
        self.period = period

    def is_permitted(self, key):
        if(self.redis.exists(key)):
            print('exists')
            count = int(self.redis.hget(key,'count'))
            blocked = float(self.redis.hget(key,'blocked'))
            start = float(self.redis.hget(key,'start'))
            print("Status : ",count,blocked,start)
            gap_time = time.time() - start

            status = {"count":1+count,"blocked":0,"start":start}
            self.redis.hset(key,mapping=status)

            print(gap_time,'gap_time',self.period,'period','Greater',gap_time > self.period)
            if(gap_time > self.period or count > self.limit):
                return False
            
            
            
            return True
            
            #check if the period betweeen now and gap_time <= period and count < limit  and block_period
            
            # self.redis.expire(key,self.period)
            # if( count> self.limit and block_period ):
            #     return True
        else:
            status = {"count":1,"blocked":0,"start":time.time()}
            print(status)
            self.redis.hset(key,mapping=status)
            print('new key added',key)
        return True
    def block(self,key,status):
        pass

       


rate_limiter = RateLimiter()
for i in range(11):
    result = rate_limiter.is_permitted('10.11.121.193')
    print("Permitted : ",result)






