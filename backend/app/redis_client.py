from redis import asyncio as aioredis

redis_client = aioredis.from_url("redis://172.19.0.2:6379", decode_responses=True)

pubsub = redis_client.pubsub()