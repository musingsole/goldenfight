import json
from websocket import create_connection
from IPython import embed

url = "wss://6zlsr9hpq3.execute-api.us-east-1.amazonaws.com/prod"
print(f"Opening socket at {url}")
ws = create_connection(url)

read_request = {
    "action": "read",
    "route": "read",
    "row": "varanus"
}
print(f"Sending read subscription request")
ws.send(json.dumps(read_request).encode("utf-8"))
print(f"Waiting on data...")
data = ws.recv()
print(f"Received: {data}")

print("Starting console\n")
embed()
