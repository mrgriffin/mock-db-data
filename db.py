r"""Parse ``infer.Schema`` objects from a database.

>>> import sqlite3
>>> connection = sqlite3.connect(":memory:")
>>> _ = connection.execute("CREATE TABLE Country (code TEXT, name TEXT)")
>>> sqlite_schemas(connection)
[Schema(table='Country', columns=[Column(name='code', type='TEXT', references=None),
                                  Column(name='name', type='TEXT', references=None)])]

>>> _ = connection.execute("CREATE TABLE User (name TEXT, country TEXT REFERENCES Country(code))")
>>> sqlite_schemas(connection)
[Schema(table='Country', columns=[...]),
 Schema(table='User', columns=[Column(name='name', type='TEXT', references=None),
                               Column(name='country', type='TEXT', references=Reference(...))])]
"""
import re

import parsec as P

from infer import Schema, Column, Reference
from parse import maybe

name = P.regex(r"\w+")
# TODO: Tie this into the types in `infer.py`.
typ = P.string("BLOB") | P.string("INT") | P.string("REAL") | P.string("TEXT")
fk = P.regex("(\s)+REFERENCES(\s)+", re.I).compose(P.joint(name.skip(P.string("(")), name.skip(P.string(")"))))
column = P.joint(name.skip(P.spaces()), typ, maybe(fk))

# TODO: Extract the name out of CREATE TABLE.
create_table = P.regex(r"CREATE(\s)+TABLE(\s)+\w+(\s)*\(", re.I) \
                .compose(P.sepBy1(column, P.regex(r"(\s)*,(\s)*"))) \
                .skip(P.regex(r"(\s)*\)"))

def sqlite_schemas(connection):
    # TODO: Does this fetch views?
    declarations = connection.execute("""SELECT name, sql FROM sqlite_master""")
    schemas = []
    for name, declaration in declarations:
        columns = []
        # TODO: Primary keys, DEFAULT, NOT NULL, and check constraints.
        for name_, typ, fk in create_table.parse_strict(declaration):
            # FIXME: Assumes that the tables only reference prior tables.
            if fk:
                [[table_, name__]] = fk
                schema_ = [s for s in schemas if s.table == table_][0]
                references = Reference(schema_, name__)
            else:
                references = None
            columns.append(Column(name_, typ, references))
        schema = Schema(name, columns)
        schemas.append(schema)
    return schemas

if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS |
                                doctest.NORMALIZE_WHITESPACE |
                                doctest.REPORT_NDIFF)
