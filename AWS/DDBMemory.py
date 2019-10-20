import boto3
import json
from datetime import datetime
from boto3.dynamodb.conditions import Key
from run_async import run_async


# Format for interpreting String Timestamps to a Datetime object or storing
# Datetime objects as String Timestamps
TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class Memory(dict):
    required_keys = ["TREE", "TRUNK"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for req_key in self.required_keys:
            if req_key not in self:
                raise Exception("{} must be defined".format(req_key))

        for key, value in self.items():
            self[key] = json.dumps(value) if not isinstance(value, str) else value


class DynamoTreeMemory:
    """ Class to encapsulate DynamoDB and tree storage model """
    @staticmethod
    def create_table(tablename):
        pass

    def __init__(self, tablename="DynamoTreeMemory"):
        self.tablename = tablename
        self.table = boto3.resource("dynamodb").Table(self.tablename)

    def memorize(self,
                 memories,
                 identifier="Unidentified"):
        """ """

        primed_memories = list({(Memory(**ob)['TREE'], Memory(**ob)['TRUNK']): ob for ob in memories}.values())
        observation_processing_deltas = []
        writestamp = datetime.utcnow()
        writestamp_string = writestamp.strftime(TIME_FORMAT)

        if len(primed_memories) > 0:
            print("Sending {} memories to {} table".format(len(primed_memories), self.tablename))

            # Store Observations in DynamoDB table
            with self.table.batch_writer() as writer:
                count = 0
                for count, memory in enumerate(primed_memories):
                    memory['WRITESTAMP'] = writestamp_string
                    if 'RECEIVESTAMP' in memory:
                        processing_delta = (writestamp - datetime.strptime(memory['RECEIVESTAMP'], TIME_FORMAT)).total_seconds()
                        observation_processing_deltas.append(processing_delta)

                    memory = Memory(**memory)
                    writer.put_item(Item=memory)

            if observation_processing_deltas:
                observation_processing_deltas = sorted(observation_processing_deltas)
                avg_processing_delta = sum(observation_processing_deltas) / len(observation_processing_deltas)
                print("AverageMemoryProcessing {} seconds".format(avg_processing_delta))
        else:
            print("No observations to upload")

    def remember(self,
                 tree,
                 root=None,
                 trunk=None,
                 branch=None,
                 **kwargs):
        if type(tree) is list:
            trees = tree
            arg_sets = [{
                "tree": tree,
                "branch": branch,
                "trunk": trunk,
                "root": root,
                **kwargs
            } for tree in trees]

            results = run_async(self.remember, arg_sets)
            memory_trees = {arg_set['tree']: mem for arg_set, mem in results}

            return memory_trees
        else:
            kce = Key("TREE").eq(tree)
            if trunk is not None:
                kce = kce & Key("TRUNK").begins_with(trunk)
            elif root is not None and branch is not None:
                kce = kce & Key("TRUNK").between(root, branch)
            elif root is not None:
                kce = kce & Key("TRUNK").gt(root)
            elif branch is not None:
                kce = kce & Key("TRUNK").lt(branch)

            kwargs['KeyConditionExpression'] = kce

            result = self.table.query(**kwargs)
            items = result['Items']

            while 'LastEvaluatedKey' in result:
                kwargs['ExclusiveStartKey'] = result['LastEvaluatedKey']
                result = self.table.query(**kwargs)
                items.extend(result['Items'])

                if 'Limit' in kwargs and len(items) >= kwargs['Limit']:
                    break

            results = [Memory(**item) for item in items]
            if 'Limit' in kwargs:
                results = results[:kwargs['Limit']]
            return results

    def forget(self, memories):
        stubborn_memories = []
        with self.table.batch_writer() as writer:
            for memory in memories:
                try:
                    writer.delete_item(
                        Key={
                            "TREE": memory['TREE'],
                            "TRUNK": memory['TRUNK']
                        }
                    )
                except Exception:
                    stubborn_memories.append(memory)

        return stubborn_memories
