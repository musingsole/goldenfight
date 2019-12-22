import json
from LambdaPage import LambdaPage
from .murd_ddb import DDBMurd


murd = DDBMurd()


class Curator:
    def __init__(self, name=""):
        pass


def update_handler(event):
    """ /update Endpoint Handler """

    # Check authorization

    # Get new mems from event
    body = json.loads(event['body'])
    mems = json.loads(body['mems'])
    identifier = body['identifier'] if 'identifier' in body else 'Unidentified'

    # Store new mems in memory
    murd.update(mems=mems, identifier=identifier)

    return 200


def read_handler(event):
    """ /read Endpoint Handler """
    # Check authorization

    # Get read constraints
    # TODO: Check query params for request
    body = json.loads(event['body'])
    row = body['row']
    col = body['col'] if 'col' in body else None
    greater_than_col = body['greater_than_col'] if 'greater_than_col' in body else None
    less_than_col = body['less_than_col'] if 'less_than_col' in body else None

    read_kwargs = {
        "row": row,
        "col": col,
        "greater_than_col": greater_than_col,
        "less_than_col": less_than_col
    }

    read = murd.read(**read_kwargs)

    return 200, json.dumps(read)


def delete_handler(event):
    """ /delete Endpoint Handler """
    # Check authorization

    # Get new mems from event
    body = json.loads(event['body'])
    mems = body['mems']
    stubborn_mems = murd.delete(mems)

    return 200, json.dumps(stubborn_mems)


def create_lambda_page():
    page = LambdaPage()
    page.add_endpoint("put", "/murd", update_handler, 'application/json')
    page.add_endpoint("put", "/murd/update", update_handler, 'application/json')
    page.add_endpoint("get", "/murd", read_handler, 'application/json')
    page.add_endpoint("get", "/murd/read", read_handler, 'application/json')
    page.add_endpoint("post", "/murd", read_handler, 'application/json')
    page.add_endpoint("post", "/murd/read", read_handler, 'application/json')
    page.add_endpoint("delete", "/murd", delete_handler, 'application/json')
    page.add_endpoint("delete", "/murd/delete", delete_handler, 'application/json')

    return page


def lambda_handler(event, handler):
    page = create_lambda_page()
    print("Received Event:\n{}".format(event))
    return page.handle_request(event)
