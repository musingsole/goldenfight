import json
from datetime import datetime, timedelta
import websocket


TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


url = "wss://8pp64nk6vl.execute-api.us-east-1.amazonaws.com/prod"


ws = websocket.WebSocket()
try:
    print("Connecting to " + url)
    ws.connect(url)

    # Request historical data within past 700 days and subscribe to new data
    historical_request = {
        "action": "request",
        "TREES": ["goldenfight"],
        "TRUNK": (datetime.utcnow() - timedelta(days=700)).strftime(TIME_FORMAT),
        "LEAF": None
    }

    print("Sending Request: {}".format(historical_request))
    ws.send(payload=json.dumps(historical_request))

    while True:
        # Process data pushes from server
        print("Waiting for pushed data")
        push = ws.recv()
        print("Received: {}".format(push))
except Exception:
    from traceback import format_exc
    print("Failed: " + format_exc())
finally:
    ws.close()
