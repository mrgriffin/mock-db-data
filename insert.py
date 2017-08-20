r"""Insert mock data into database.

Inserts into the tables without FKs first:
>>> c = Schema("Country", [Column("code", "TEXT", None),
...                        Column("name", "TEXT", None)])
>>> u = Schema("User", [Column("name", "TEXT", None),
...                     Column("country", "TEXT", Reference(c, "code"))])
>>> o = Schema("Order", [Column("id", "INT", None),
...                      Column("user", "TEXT", Reference(u, "name"))])
>>> order({c, u, o})
[Schema(table='Country', ...), Schema(table='User', ...), Schema(table='Order', ...)]

>>> connection = sqlite3.connect(":memory:")
>>> _ = connection.execute("CREATE TABLE Country (code TEXT, name TEXT)")
>>> _ = connection.execute("CREATE TABLE User (name TEXT, country TEXT REFERENCES Country(code))")
>>> rows = {c: [{"code": "GB", "name": "Great Britain"}],
...         u: [{"name": "Bob", "country": "GB"},
...             {"name": "Jim", "country": "GB"}]}
>>> insert(connection, rows)
>>> list(connection.execute("SELECT code, name FROM Country"))
[('GB', 'Great Britain')]
>>> list(connection.execute("SELECT name, country FROM User"))
[('Bob', 'GB'), ('Jim', 'GB')]
"""
import toposort

def order(schemas):
    dependencies = {s: {c.references.table for c in s.columns if c.references}
                    for s in schemas}
    return toposort.toposort_flatten(dependencies)

def insert(connection, rows):
    for schema in order(rows):
        rows_ = rows[schema]
        connection.executemany("""
            INSERT INTO {table} ({columns})
                 VALUES ({placeholders})
            """.format(table=schema.table,
                       columns=", ".join(c.name for c in schema.columns),
                       placeholders=", ".join(":{}".format(c.name) for c in schema.columns)),
            rows_)

if __name__ == "__main__":
    import sqlite3
    from infer import Schema, Column, Reference

    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS |
                                doctest.NORMALIZE_WHITESPACE |
                                doctest.REPORT_NDIFF)
