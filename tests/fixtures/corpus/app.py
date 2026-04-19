import json
import sqlite3


def export_graph(records):
    connection = sqlite3.connect(":memory:")
    connection.execute("create table items (payload text)")
    for record in records:
        connection.execute("insert into items (payload) values (?)", (json.dumps(record),))
    return json.dumps(records)
