from traceback import format_exc as generate_traceback


success = 200
failure = 500


class lambda_route_event(dict):
    def __init__(self, route=None, **kwargs):
        super().__init__(**kwargs)
        if route is None:
            route = "$default"

        self['requestContext'] = {'routeKey': route}


def route_from_event(event):
    if 'routeKey' in event:
        return event['routeKey']
    elif 'requestContext' in event and 'routeKey' in event['requestContext']:
        return event['requestContext']['routeKey']
    else:
        raise Exception("Route not found in event")


def connection_id_from_event(event):
    if 'requestContext' in event and 'connectionId' in event['requestContext']:
        return event['requestContext']['connectionId']
    else:
        raise Exception("Connection ID not found in event")


class LambdaSocket:
    def __init__(self):
        self.endpoints = {}

    def add_endpoint(self, route, func, content_type='application/json', enable_caching=False):
        if route not in self.endpoints:
            self.endpoints[route] = {}
        func.content_type = content_type
        self.endpoints[route] = func

    def handle_request(self, event, log=lambda x: None):
        try:
            route = route_from_event(event)
        except Exception:
            log("Route Extraction failed. Returning failure")
            return {"statusCode": failure}

        if route not in self.endpoints:
            log("Route {} Not found".format(route))
            return {"statusCode": failure}

        func = self.endpoints[route]

        try:
            log("Executing Socket Request")
            func(event)
            return {"statusCode": success}
        except Exception as e:
            print("Socket Request Failed:\n{}".format(generate_traceback()))
            return {"statusCode": failure}
