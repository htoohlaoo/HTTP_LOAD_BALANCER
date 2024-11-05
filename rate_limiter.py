import redis
import time
import json
import hashlib
class RateLimiter:
    def __init__(self, redis_client=redis.Redis(host='localhost', port=6379, db=0), limit=10, period=30,block_period=60):
        self.redis = redis_client
        self.limit = limit
        self.period = period
        self.block_period = block_period
    def hash_key(self,data): 
        hasher = hashlib.sha256()
        hasher.update(bytes(data,encoding='utf-8'))
        return hasher.hexdigest()

    def is_permitted(self, key):
        key = self.hash_key(key)
        if(self.redis.exists(key)):
            print('exists')
            count = int(self.redis.hget(key,'count'))
            blocked = float(self.redis.hget(key,'blocked'))
            start = float(self.redis.hget(key,'start'))

            gap_time = time.time() - start
            
            

            status = {"count":1+count,"blocked":0,"start":start}
            
            print("Before Status : ",count,blocked,start)
            block_gap = time.time()-blocked
            
            
            if( gap_time> self.period ):
                status = {"count":1,"blocked":blocked,"start":time.time()}

            if(block_gap >= self.block_period):
                self.unblock(key,status)


            self.redis.hset(key,mapping=status)
            print(gap_time,'gap_time',self.period,'period','Greater',gap_time > self.period)
            print("Status : ",count,blocked,start)
            
            if(self.is_blocked(key) and block_gap < self.block_period):
                    
                print("Blocked...")
                return False
            
            if(gap_time < self.period and count >= self.limit ):
                self.block(key,status)
                return False
            
            return True
            
        else:
            status = {"count":1,"blocked":0,"start":time.time()}
            print(status)
            self.redis.hset(key,mapping=status)
            print('new key added',key)
        return True
    def block(self,key,status):
        print("Blocked IP : ",key)
        status = {"count":status['count'],'blocked':time.time()+self.period,"start":status['start']}
        self.redis.hset(key,mapping=status)
        #add ip to blocked_list
        self.redis.sadd('blocked_list',key)
        return
    def unblock(self,key,status):
        print("UnBlocked IP : ",key)
        status = {"count":status['count'],'blocked':0,"start":status['start']}
        self.redis.hset(key,mapping=status)
        #add ip to blocked_list
        self.redis.srem('blocked_list',key)
        return
    def is_blocked(self,key):
        return self.redis.sismember('blocked_list',key)

       








