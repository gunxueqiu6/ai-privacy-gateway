# -*- coding: utf-8 -*-
import os, asyncio
from config import config
from gateway_core import GatewayCore

print('TARGET_LLM before:', config.TARGET_LLM)
config.TARGET_LLM = "http://127.0.0.1:1"
print('TARGET_LLM after:', config.TARGET_LLM)
gw = GatewayCore()
print('gw.target_url:', gw.target_url)
lb = gw.load_balancer
print('lb type:', type(lb).__name__)
try:
    print('lb upstreams:', lb.upstreams)
except Exception as e:
    print('lb upstreams err:', e)

async def run():
    return await gw.proxy_request({"test": True}, {"Authorization": "Bearer x"}, {}, "test-session")

status, body, headers = asyncio.run(run())
print('RESULT status:', status)
