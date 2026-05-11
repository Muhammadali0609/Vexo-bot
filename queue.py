import os
import json
import redis

r = redis.from_url(os.getenv("REDIS_URL"))

def add_task(task):
    r.lpush("tasks", json.dumps(task))

def get_task():
    task = r.brpop("tasks")
    return json.loads(task[1])
