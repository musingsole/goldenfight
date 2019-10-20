from DDBMemory import Memory, DynamoTreeMemory


class GatewayHandler(DynamoTreeMemory):
    pass


class HTTPHandler(GatewayHandler):
    def post_data
        pass

    def get_data
        pass

    def register
        pass


class WebSocketHandler(GatewayHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = True

    def get_active_connections(self):
        active_connections = self.remember(root="connections")

        if self.log:
            print("Returning Active Connections {}".format(active_connections))
        return active_connections

    def get_active_connection(self, connection_id):
        if self.log:
            print("Recovering connection for " + connection_id)

        active_connection = self.remember(
            root="connections",
            branch=connection_id
        )

        if self.log:
            print("Returning: {}".format(active_connection))

        return active_connection

    def add_active_connection(self, connection_id):
        cid_memory = Memory(TREE="connections", TRUNK=connection_id)
        if self.log:
            print("Adding Connection: {}".format(cid_memory))
        self.memorize([cid_memory])

    def remove_connection(self, connection_id, suppress_missing=False):
        cid_memory = Memory(TREE="connections", TRUNK=connection_id)
        if self.log:
            print("Removing Connection: {}".format(cid_memory))
        self.forget([cid_memory])
