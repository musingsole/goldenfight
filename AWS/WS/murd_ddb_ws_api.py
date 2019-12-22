import json
from collections import defaultdict
from uuid import uuid4
import boto3
from .murd_ddb import DDBMurd, MurdMemory


murd = DDBMurd()

CID_UUID_DELIMITER = ">><<"


class Curator:
    def __init__(self, name=""):
        pass


def connect_handler(event):
    """ Handle new connetions to WS"""
    print("Handling connection")
    connection_id = event['requestContext']['connectionId']
    host = event['requestContext']['domainName']
    print(f"From '{connection_id}' at '{host}'")
    murd.update([MurdMemory(ROW="ws_connections",
                            COL=connection_id,
                            HOST=host)],
                identifier="murd_ddb_ws_api")
    return {"statusCode": 200}


def disconnect_handler(event):
    """ Handle disconnections from WS"""
    print("Handling disconnection")
    connection_id = event['requestContext']['connectionId']
    print(f"From {connection_id}")
    murd.delete([MurdMemory(ROW="ws_connections",
                            COL=connection_id)],
                identifier="murd_ddb_ws_api")
    return {"statusCode": 200}


def update_handler(body):
    """ /update Endpoint Handler """

    # Check authorization

    # Get new mems from event
    mems = json.loads(body['mems'])
    identifier = body['identifier'] if 'identifier' in body else 'Unidentified'

    # Store new mems in memory
    murd.update(mems=mems, identifier=identifier)

    return {"statusCode": 200}


def read_handler(connection_id, body):
    """ /read Endpoint Handler """
    # Check authorization

    # Get read constraints
    # TODO: Check query params for request
    request = json.loads(body['request'])
    row = request['row']
    col = request['col'] if 'col' in request else None
    greater_than_col = request['greater_than_col'] if 'greater_than_col' in request else None
    less_than_col = request['less_than_col'] if 'less_than_col' in request else None

    read_kwargs = {
        "row": row,
        "col": col,
        "greater_than_col": greater_than_col,
        "less_than_col": less_than_col
    }

    subscription_memory = MurdMemory(
        ROW="ws_subscriptions",
        COL=f"{connection_id}{CID_UUID_DELIMITER}{uuid4()}",
        SUBSCRIPTION=read_kwargs
    )
    murd.update([subscription_memory], identifier="MurdWSClientSubscribe")

    return {"statusCode": 200}


def delete_handler(body):
    """ /delete Endpoint Handler """
    # Check authorization

    # Get new mems from event
    mems = json.loads(body['mems'])
    stubborn_mems = murd.delete(mems)

    return {"statusCode": 200, "stubborn_mems": stubborn_mems}


def default_handler(event):
    """ Handle unrecognized routes"""
    connection_id = event['requestContext']['connectionId']
    body = json.loads(event['body'])
    if body['route'] == 'update':
        return update_handler(body)
    elif body['route'] == 'read':
        return read_handler(connection_id, body)
    elif body['route'] == 'delete':
        return delete_handler(body)
    else:
        print(f"Unrecognized route: {body['route']}")
        return {"statusCode": 200}


def serve_subscribers(event):
    print("Serving subscribers")
    subscriptions = murd.read(row="ws_subscriptions")
    subs_by_cid = defaultdict(lambda: [])
    for sub in subscriptions:
        subs_by_cid[sub['COL'].split(CID_UUID_DELIMITER)[0]].append(sub)
    for cid, subs in subs_by_cid.items():
        try:
            print(f"Checking for {cid} connection")
            connection = murd.read(row="ws_connections", col=cid)[0]
            print("Connection confirmed")
        except IndexError:
            print(f"Connection {cid} expired")
            murd.delete(subs)
            continue

        data = []
        for sub in subs:
            read_kwargs = json.loads(sub['SUBSCRIPTION'])
            print("Sub: {}".format(sub))
            print(f"Reading with {read_kwargs}")
            mems = murd.read(**read_kwargs)
            data.extend(mems)
        endpoint_url = f"https://{connection['HOST']}/prod"
        print(f"Sending data to {endpoint_url}")
        filled_subscription = {"data": data, "meta_data": "foo"}
        client = boto3.client('apigatewaymanagementapi',
                              endpoint_url=endpoint_url)
        client.post_to_connection(
            Data=json.dumps(filled_subscription).encode('utf-8'),
            ConnectionId=cid)


def lambda_handler(event, lambda_context):
    print("Received Event:\n{}".format(event))

    if 'serve_subscribers' in event:
        serve_subscribers(event)
    elif 'requestContext' in event:
        request_context = event['requestContext']
        if '$connect' == request_context['routeKey']:
            return connect_handler(event)
        elif '$disconnect' == request_context['routeKey']:
            return disconnect_handler(event)
        else:
            return default_handler(event)
    else:
        print("Unrecognized Event")
        serve_subscribers(None)


if __name__ == "__main__":
    serve_subscribers(None)
