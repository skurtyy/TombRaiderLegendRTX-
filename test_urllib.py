import urllib.request
import urllib.error
import json

payload = json.dumps({
    'model': 'claude-haiku-4-5-20251001', # Wait, haiku-4-5? Actually haiku 3.5 is latest? Wait. Is claude-haiku-4-5-20251001 a real model? NO. Claude 3.5 Haiku is claude-3-5-haiku-20241022.
    'max_tokens': 32,
    'system': 'test',
    'messages': [{'role': 'user', 'content': 'hello'}]
}).encode()

req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=payload, headers={
    'Content-Type': 'application/json',
    'x-api-key': 'fake-key',
    'anthropic-version': '2023-06-01'
})

try:
    with urllib.request.urlopen(req) as r:
        print(r.read())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read())
