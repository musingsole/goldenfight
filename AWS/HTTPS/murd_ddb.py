from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from .murd import Murd, MurdMemory
from .run_async import run_async, default_log


def list_all_tablenames():
    ddb = boto3.client("dynamodb")
    resp = ddb.list_tables()
    tablenames = resp['TableNames']
    while 'LastEvaluatedTableName' in resp:
        resp = ddb.list_tables(ExclusiveStartTableName=resp['LastEvaluatedTableName'])
        tablenames.extend(resp['TableNames'])

    return tablenames


def create_ddb_table(name):
    ddb = boto3.client("dynamodb")
    ddb.create_table(
        TableName=name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {
                'AttributeName': 'ROW',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'COL',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'ROW',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'COL',
                'KeyType': 'RANGE'
            }
        ]
    )


class DDBMurd(Murd):
    """ DynamoDB Implementation of Murd """

    def get_murds(self):
        tablenames = list_all_tablenames()

        mem_tables = [table for table in tablenames if self.name in table]

        ddb = boto3.resource("dynamodb")
        self.tables = {tablename: ddb.Table(tablename) for tablename in mem_tables}

        return self.tables

    def create_murd(self, suffix=""):
        dt = datetime.utcnow().isoformat()[:10]
        name = "{}{}.{}".format(self.name, suffix, dt)
        create_ddb_table(name)
        self.get_murds()

    def __init__(self, name='murd', **kwargs):
        kwargs['name'] = name
        super().__init__(**kwargs)

        self.get_murds()

        if len(self.tables) == 0:
            self.create_murd(name)
            self.get_murds()

    def get_latest_murd(self):
        keys = list(self.tables.keys())
        keys = sorted(keys, reverse=True)
        return self.tables[keys[0]]

    def update(self,
               mems,
               identifier="Unidentified"):
        primed_mems = self.prime_mems(mems)

        if len(primed_mems) > 0:
            latest_murd = self.get_latest_murd()
            print("Sending {} mems to {} table".format(len(primed_mems), latest_murd.table_name))

            # Store Memories in DynamoDB table
            with latest_murd.batch_writer() as writer:
                count = 0
                for count, mem in enumerate(primed_mems):
                    mem = MurdMemory(**mem)
                    writer.put_item(Item=mem)
        else:
            print("No observations to upload")

    def complete_table_query(self, table, kwargs):
        query_result = table.query(**kwargs)
        items = query_result['Items']

        while 'LastEvaluatedKey' in query_result:
            kwargs['ExclusiveStartKey'] = query_result['LastEvaluatedKey']
            query_result = table.query(**kwargs)
            items.extend(query_result['Items'])

            if 'Limit' in kwargs and len(items) >= kwargs['Limit']:
                break

        results = [MurdMemory(**item) for item in items]
        if 'Limit' in kwargs:
            results = results[:kwargs['Limit']]

        return results

    def read(self,
             row,
             col=None,
             greater_than_col=None,
             less_than_col=None,
             **kwargs):
        if type(row) is list:
            rows = row
            arg_sets = [{
                "row": row,
                "col": col,
                "greater_than_col": greater_than_col,
                "less_than_col": less_than_col,
                **kwargs
            } for row in rows]

            results = run_async(self.read, arg_sets)
            mem_mems = {arg_set['mem']: mem for arg_set, mem in results}

            return mem_mems

        else:
            kce = Key("ROW").eq(row)
            if col is not None:
                kce = kce & Key("COL").begins_with(col)

            elif greater_than_col is not None and less_than_col is not None:
                kce = kce & Key("COL").between(greater_than_col, less_than_col)

            elif greater_than_col is not None:
                kce = kce & Key("COL").gt(greater_than_col)
            elif less_than_col is not None:
                kce = kce & Key("COL").lt(less_than_col)

            kwargs['KeyConditionExpression'] = kce

            arg_sets = [[table, kwargs] for table in self.tables.values()]
            arg_sets, results = zip(*run_async(self.complete_table_query, arg_sets, log=default_log))

            items = []
            for results in results:
                items.extend(results)

            mems = [MurdMemory(**item) for item in items]
            return mems

    def delete_from_table(self, table, mems):
        stubborn_mems = []
        with table.batch_writer() as writer:
            for mem in mems:
                try:
                    writer.delete_item(
                        Key={
                            "ROW": mem['ROW'],
                            "COL": mem['COL']
                        }
                    )
                except Exception:
                    stubborn_mems.append(mem)

        return stubborn_mems

    def delete(self, mems):
        arg_sets = [[table, mems] for table in self.tables.values()]
        run_async(self.delete_from_table, arg_sets, log=default_log)
