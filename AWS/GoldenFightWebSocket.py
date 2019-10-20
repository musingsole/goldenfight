import boto3
from LambdaSocket import LambdaSocket, connection_id_from_event
from DDBMemory import DynamoTreeMemory, TIME_FORMAT
from WebSocketMemory import WebSocketMemory
import json
import requests
from requests_aws_sign import AWSV4Sign
from urllib.parse import quote
from traceback import format_exc as generate_traceback
from datetime import datetime
from collections import defaultdict
from dateutil.parser import parse as parse_datestring
import pytz


memory = DynamoTreeMemory("GoldenFight")

ONLINE = True


###############################################################################


def get_api_id():
    try:
        api_id = [api for api in boto3.client(
            "apigatewayv2"
        ).get_apis()['Items'] if 'goldenfight-websocket' in api['Name']][0]['ApiId']
        return api_id
    except Exception:
        raise Exception("Failed to find API Id:\n{}".format(generate_traceback()))


def send_data(data, connection_id):
    endpoint = "https://{api_id}.execute-api.{region}.amazonaws.com/{stage}/@connections/{connection_id}"
    session = boto3.Session()
    credentials = session.get_credentials()

    api_id = get_api_id()
    fe = endpoint.format(
        connection_id=quote(connection_id),
        api_id=api_id,
        region=session.region_name,
        stage="prod"
    )

    # ak = "AKIAI2VOK2U3MAWQFZSA"
    # sk = "DHfNU5C2fqhS6CB0gdLCZqPqheqAdiMFS9A9jTVN"
    auth = AWSV4Sign(
        credentials,
        session.region_name,
        'execute-api'
    )

    resp = requests.post(fe, json=data, auth=auth)

    if resp.status_code != 200:
        raise Exception("Failed data post: {}:{}".format(resp.status_code, resp.text))


def default(event):
    print("Processing Default Event: {}".format(event))
    if 'body' in event and 'spawn' in event['body']:
        body = json.loads(event['body'])
        spawn_command = body['spawn']

        print("Received Spawn Command: {}".format(spawn_command))
    else:
        raise Exception("Unrecognized request")


def connect(event):
    print("Processing Connect Event: {}".format(event))

    connection_id = connection_id_from_event(event)

    print("Adding connection id to active list")
    wsm = WebSocketMemory(memory.tablename)
    wsm.add_active_connection(connection_id)


def disconnect(event):
    print("Processing Disconnect Event: {}".format(event))

    connection_id = connection_id_from_event(event)

    print("Remove Connection Id from subscriptions")
    wsm = WebSocketMemory(memory.tablename)
    wsm.remove_connection(connection_id)


def data_request_trunk_to_cid(trunk):
    return trunk.split("|||||")[0].strip()


def cid_id_to_trunk(cid, request_identifier):
    return "{} ||||| Request {}".format(cid, request_identifier)


def prune_inactive_requests(data_requests, connections):
    print("Organizing by Connection Id")
    requests_by_cid = defaultdict(lambda: [])
    for dr in data_requests:
        cid = data_request_trunk_to_cid(dr['TRUNK'])
        requests_by_cid[cid].append(dr)

    active_cids = [conn['TRUNK'] for conn in connections]

    print("Dropping requests from inactive Connection Ids")
    active_data_requests = []
    for cid, cid_dr in requests_by_cid.items():
        if cid not in active_cids:
            print("Dropping requests from {}".format(cid))
            memory.forget(cid_dr)
        else:
            active_data_requests.append(cid_dr)

    active_data_requests = [dr for adrs in active_data_requests for dr in adrs]

    return active_data_requests


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def spawn_servicer(event=None):
    lambda_client = boto3.client("lambda")

    if event is None:
        event = {"routeKey": "service"}
    else:
        event['routeKey'] = "service"

    if ONLINE:
        resp = lambda_client.invoke(
            FunctionName="GoldenFightWebSocketServiceRequest",
            InvocationType='Event',
            Payload=json.dumps(event).encode()
        )

        if not 200 <= resp['StatusCode'] < 300:
            raise Exception("Failed to spawn servier: {}".format(resp))
    else:
        return service_request({})


def service_request(event):
    if 'SERVICE_LIMIT' in event:
        service_limit = float(event['SERVICE_LIMIT'])
    else:
        service_limit = 5

    print("Service Request")
    if 'data_requests' not in event:
        data_requests = memory.remember(tree="data_requests")
    else:
        data_requests = json.loads(event['data_requests'])

    print("Found {} requests".format(len(data_requests)))

    print("Retrieving active connections")
    connections = WebSocketMemory(memory.tablename).get_active_connections()

    data_requests = prune_inactive_requests(data_requests, connections)

    print("Attempting to service {} requests".format(len(data_requests)))
    to_forget = []
    for data_request in data_requests[:service_limit]:
        connection_id = data_request_trunk_to_cid(data_request['TRUNK'])
        trunk = data_request['REQUEST_TRUNK'] if 'REQUEST_TRUNK' in data_request else None
        root = data_request['REQUEST_ROOT'] if 'REQUEST_ROOT' in data_request else None
        branch = data_request['REQUEST_BRANCH'] if 'REQUEST_BRANCH' in data_request else None
        tree = data_request['REQUEST_TREE']

        if 'Limit' in data_request:
            data_request['Limit'] = int(data_request['Limit'])

        if 'ScanIndexForward' in data_request:
            data_request['ScanIndexForward'] = json.loads(data_request['ScanIndexForward'])

        nonkwargs = ["action", "TRUNK", "TREE", "WRITESTAMP", "REQUEST_TREE", "REQUEST_TRUNK", "REQUEST_ROOT", "REQUEST_BRANCH"]
        request_kwargs = {key: value for key, value in data_request.items() if key not in nonkwargs}
        request_kwargs = {'tree': tree, 'root': root, 'trunk': trunk, 'branch': branch, **request_kwargs}
        print("Memory request: {}".format(request_kwargs))
        memories = memory.remember(**request_kwargs)

        print("Recovered {} memories".format(len(memories)))
        for memory_chunk in chunks(memories, 500):
            try:
                send_data(memory_chunk, connection_id)
            except Exception:
                print("Failed to send data to connection")
                print(generate_traceback())

        try:
            branchdate = parse_datestring(str(branch)).astimezone(pytz.utc)
            if branchdate > datetime.utcnow():
                print("Removing serviced data request")
                to_forget.append(data_request)
        except ValueError:
            print("Branch is not date-like")

        try:
            data_request['REQUEST_ROOT'] = datetime.utcnow().strftime(TIME_FORMAT)
            memory.memorize([data_request])
        except Exception:
            print("Unable to update request with completed time")

    print("Removing completed requests")
    memory.forget(to_forget)

    leftover = data_requests[service_limit:]

    if leftover:
        print("{} more requests. Spawning new servicer".format(len(leftover)))
        event = {"routeKey": "service", "data_requests": leftover}
        spawn_servicer()


def request(event):
    print("Processing Request Event: {}".format(event))
    connection_id = connection_id_from_event(event)
    memory_request = json.loads(event['body'])

    # TODO: Validate memory request

    # Find existing requests from connection
    existing_requests = memory.remember(tree="data_requests", root=connection_id)

    # Register memory request
    memory_request["TREE"] = "data_requests"
    memory_request["TRUNK"] = cid_id_to_trunk(connection_id, len(existing_requests))
    memory.memorize([memory_request])

    # Spawn Data fulfiller
    spawn_servicer()


def upload(event):
    print("Processing Upload Event")
    try:
        body = json.loads(event['body'])
        memories = body['memories']
        memory.memorize(memories, identifier="GoldenFightUpload")
    except Exception as e:
        print("Failed: {}".format(e))
        raise

    spawn_servicer()


def unsubscribe(event):
    print("Processing Unsubscribe Request: {}".format(event))
    connection_id = json.loads(event['body'])['connection_id']

    print("Gathering active requests")
    data_requests = memory.remember(tree="data_requests", trunk=connection_id)
    print("Found {} requests".format(len(data_requests)))

    print("Dropping requests")
    memory.forget(data_requests)

    spawn_servicer()


###############################################################################

def init_lambda_page():
    socket = LambdaSocket()

    socket.add_endpoint(route="$connect", func=connect)
    socket.add_endpoint(route="$disconnect", func=disconnect)
    socket.add_endpoint(route="$default", func=default)
    socket.add_endpoint(route="request", func=request)
    socket.add_endpoint(route="upload", func=upload)
    socket.add_endpoint(route="unsubscribe", func=unsubscribe)
    socket.add_endpoint(route="service", func=service_request)

    return socket


def lambda_handler(event, context):
    print("Received Event: {}".format(event))
    resp = init_lambda_page().handle_request(event, log=print)
    print("Returning Resp: {}".format(resp))
    return resp


if __name__ == "__main__":
    ONLINE = False
    event = {"routeKey": "service"}
    print(lambda_handler(event, None))
