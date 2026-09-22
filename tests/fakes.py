class FakeRedis:
    def __init__(self):
        self.calls = []
        self.error = None
        self.reply = None

    async def xadd(self, key, fields):
        self.calls.append(("xadd", key, fields))
        return "1710000000000-0"

    async def xgroup_create(self, key, group, id="0", mkstream=False):
        self.calls.append(("xgroup", key, group, id, mkstream))
        if self.error is not None:
            raise self.error

    async def xreadgroup(self, groupname, consumername, streams, count, block):
        self.calls.append(("xreadgroup", groupname, consumername, streams, count, block))
        return self.reply

    async def xack(self, key, group, *ids):
        self.calls.append(("xack", key, group, ids))
        return len(ids)


class FakeSession:
    def __init__(self, rows=None):
        self.statements = []
        self.added = []
        self.rows = list(rows or [])

    async def execute(self, statement):
        self.statements.append(statement)

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        return None

    async def scalars(self, statement):
        self.statements.append(statement)
        rows = list(self.rows)

        class Result:
            def all(self):
                return rows

        return Result()
