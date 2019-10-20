import json
import os
from WiPyFunctions import get_timestamp
from run_async import run_async


class Memory(dict):
    required_keys = ["TREE", "TRUNK"]

    def __init__(self, **kwargs):
        self = kwargs
        for req_key in Memory.required_keys:
            if req_key not in self:
                raise Exception("{} must be defined".format(req_key))

        for key, value in self.items():
            self[key] = json.dumps(value) if not isinstance(value, str) else value


class woodwell:
    """ woodwell represents a collection of tree-like memory structures
        stored in a key-value store system. Initial storage system backends
        are:
            Primary: String
            Secondary: DynamoDB
            Tertiary: S3, local filestore

        Challenges:
            Primary:
                * Table Creation
                * Simultanenous Request

            Secondary/Tertiary:
                * Optimize file system (directory, folder, contents) for S3 or
                  locally managed key-value store
    """

    tree_trunk_sep = "|||||"

    def __init__(
        self,
        name='',
        woodwell='{}',
        woodwells=[],
        **kwargs
    ):
        if name == '':
            self.name = 'woodwell'

        self.woodwell = woodwell
        self.woodwells = woodwells
        self.woodwells.append(self)

    @staticmethod
    def prime_memories(memories):
        return list({(Memory(**ob)['TREE'], Memory(**ob)['TRUNK']): ob for ob in memories}.values())

    @staticmethod
    def mem_to_key(mem):
        return "{}{}{}".format(mem['TREE'], woodwell.tree_trunk_sep, mem['TRUNK'])

    def memorize(
        self,
        memories,
        identifier="Unidentified"
    ):
        primed_memories = self.prime_memories(memories)
        creationstamp_string = get_timestamp()

        woodwell = json.loads(self.woodwell)

        if len(primed_memories) > 0:
            print("Storing {} memories".format(len(primed_memories)))

            for count, memory in enumerate(primed_memories):
                memory['CREATIONSTAMP'] = creationstamp_string
                woodwell[self.mem_to_key(memory)] = memory

        self.woodwell = json.dumps(woodwell)

    def local_remember(
        self,
        tree,
        root=None,
        trunk=None,
        **kwargs
    ):
        woodwell = json.loads(self.woodwell)
        keys = list(woodwell.keys())
        prefix = str(tree)
        if trunk is not None:
            prefix += str(trunk)
        matched = [key for key in keys if prefix in key]
        results = [Memory(**woodwell[key]) for key in matched]

        if 'Limit' in kwargs:
            results = results[:int(kwargs['Limit'])]

        return results

    def remember(
        self,
        tree,
        root=None,
        trunk=None,
        **kwargs,
    ):
        if type(tree) is list:
            arg_sets = []
            trees = tree
            for tree in trees:
                arg_kwargs = {key: value for key, value in kwargs.items()}
                arg_kwargs['tree'] = tree
                arg_kwargs['trunk'] = tree
                arg_kwargs['root'] = root
                arg_sets.append(arg_kwargs)

            results = run_async(self.remember, arg_sets)
            memory_trees = {arg_set['tree']: mem for arg_set, mem in results}

            return memory_trees
        else:
            arg_set = {key: value for key, value in kwargs.items()}
            arg_set['tree'] = tree
            arg_set['trunk'] = trunk
            arg_set['root'] = root

            results = []
            for woodwell in self.woodwells:
                ww_results = woodwell.local_remember(**arg_set)
                results.extend(ww_results)

            return results

    def forget(self, memories):
        woodwell = json.loads(self.woodwell)
        primed_memories = self.prime_memories(memories)
        keys = [self.mem_to_key(m) for m in primed_memories]
        for key in keys:
            if key not in woodwell:
                raise Exception("Memory {} not found!".format(key))

        for key in keys:
            woodwell.pop(key)

        self.woodwell = json.dumps(woodwell)

    def assimilate(
        self,
        foreign_woodwell
    ):
        """ Become aware of other woodwell so as to read it as well """
        self.woodwells.append(foreign_woodwell)

    def absorb(
        self,
        foreign_woodwell
    ):
        pass

    def __str__(self):
        return self.woodwell
