import requests
import json

def send_line_broadcast(token, msg):
    if not token: return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try: 
        requests.post(url, headers=headers, data=json.dumps({"messages": [{"type": "text", "text": msg}]}))
    except: 
        pass