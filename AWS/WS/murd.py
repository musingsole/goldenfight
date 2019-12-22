import json


class MurdMemory(dict):
    required_keys = ["ROW", "COL"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for req_key in self.required_keys:
            if req_key not in self:
                raise Exception("{} must be defined".format(req_key))

        for key, value in self.items():
            self[key] = json.dumps(value) if not isinstance(value, str) else value


class Murd:
    """ Murd - Matrix: Update, Read, Delate - represents a collection of map memory structures
        stored in a key-value store system.

        Backends:
            Primary: String - JSON, CSV
            Secondary: DynamoDB
            Tertiary: S3, local filestore
    """

    row_col_sep = "|||||"

    def __init__(
        self,
        name='',
        murd='{}',
        murds=[],
        **kwargs
    ):
        self.name = name

        self.murd = murd

    @staticmethod
    def prime_mems(mems):
        return list({(MurdMemory(**mem)['ROW'], MurdMemory(**mem)['COL']): mem for mem in mems}.values())

    @staticmethod
    def mem_to_key(mem):
        return "{}{}{}".format(mem['ROW'], Murd.row_col_sep, mem['COL'])

    @staticmethod
    def row_col_to_key(row, col):
        return "{}{}{}".format(row, Murd.row_col_sep, col)

    def update(
        self,
        mems,
        identifier="Unidentified"
    ):
        primed_mems = self.prime_mems(mems)

        murd = json.loads(self.murd)

        if len(primed_mems) > 0:
            print("Storing {} memories".format(len(primed_mems)))

            for count, mem in enumerate(primed_mems):
                murd[self.mem_to_key(mem)] = mem

        self.murd = json.dumps(murd)

    def read(
        self,
        row,
        col=None,
        greater_than_col=None,
        less_than_col=None,
        **kwargs
    ):
        murd = json.loads(self.murd)

        matched = list(murd.keys())
        if col is not None:
            prefix = "{}{}{}".format(row, Murd.row_col_sep, col)
            matched = [key for key in matched if prefix in key]

        if less_than_col is not None:
            maximum = self.row_col_to_key(row, less_than_col)
            matched = [key for key in matched if key < maximum]

        if greater_than_col is not None:
            minimum = self.row_col_to_key(row, greater_than_col)
            matched = [key for key in matched if key > minimum]

        results = [MurdMemory(**murd[key]) for key in matched]

        if 'Limit' in kwargs:
            results = results[:kwargs['Limit']]

        return results

    def delete(self, mems):
        murd = json.loads(self.murd)
        primed_mems = self.prime_mems(mems)
        keys = [self.mem_to_key(m) for m in primed_mems]
        for key in keys:
            if key not in murd:
                raise Exception("MurdMemory {} not found!".format(key))

        for key in keys:
            murd.pop(key)

        self.murd = json.dumps(murd)

    def join(
        self,
        foreign_murd
    ):
        """ Join foreign murd into this murd structure """
        raise Exception("Not implemented")

    def __str__(self):
        return self.murd

    def csv_string(self):
        murd = json.loads(self.murd)
        cols = []
        for key, mem in murd.items():
            new_cols = list(mem.keys())
            cols.extend(new_cols)
            cols = list(set(cols))
        csv_string = "key," + ",".join(cols) + "\n"
        for key, mem in murd.items():
            csv_row = key
            for col in cols:
                csv_row += ","
                if col in mem:
                    csv_row += str(mem[col])
            csv_row += "\n"
            csv_string += csv_row
        return csv_string
