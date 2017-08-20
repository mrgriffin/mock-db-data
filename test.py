r'''Decorator that parses SQL tests in docstrings.

>>> connection = sqlite3.connect(":memory:")
>>> connection.row_factory = sqlite3.Row
>>> _ = connection.execute("CREATE TABLE Country (code TEXT, name TEXT)")
>>> _ = connection.execute("CREATE TABLE User (name TEXT, country TEXT REFERENCES Country(code))")
>>> schemas = sqlite_schemas(connection)

Given sections are a sequence of ``SELECT *``s and resulting data:
>>> _ = given.parse_strict("\n".join([
... "SELECT * FROM Country;",
... "+------+---------------+",
... "| code | name          |",
... "+------+---------------+",
... "| GB   | Great Britain |",
... "+------+---------------+",
... "SELECT * FROM User;",
... "+------+---------+",
... "| name | country |",
... "+------+---------+",
... "| Bob  | GB      |",
... "+------+---------+",
... ]))
>>> _ == [("Country", [{"code": "GB", "name": "Great Britain"}]),
...       ("User", [{"name": "Bob", "country": "GB"}])]
True

>>> @dbtest(connection)
... def test(countries, c, d):
...     """
...     SELECT * FROM User;
...     +------+---------+
...     | name | country |
...     +------+---------+
...     | Bob  | :c      |
...     | Jim  | :d      |
...     +------+---------+
...
...     SELECT * FROM Country;
...     """
...     assert {c["code"] for c in countries} == {c, d}
>>> test()

Placeholders are shared between each ``SELECT``:
>>> @dbtest(connection)
... def test(user_countries, c):
...     """
...     SELECT * FROM Country;
...     +------+------+
...     | code | name |
...     +------+------+
...     | :c   | USA  |
...     +------+------+
...     SELECT * FROM User;
...     +------+---------+
...     | name | country |
...     +------+---------+
...     | Jim  | :c      |
...     +------+---------+
...
...     SELECT u.name, c.name FROM User u JOIN Country c on u.country=c.code;
...     """
...     [jim] = user_countries
...     assert tuple(jim) == ("Jim", "USA")
>>> test()
'''
from functools import wraps
import re
import textwrap

import parsec as P

from infer import expand, references
from insert import insert
from parse import table
from db import name, sqlite_schemas

# TODO: Support naming columns (and enforce in `parse.table`).
# TODO: Support `JOIN`s to simplify typing?
# TODO: Flatten adjacent spaces pre-parse to enhance readability here.
select = P.regex(r"SELECT(\s)+\*(\s)+FROM(\s)+", re.I).compose(name).skip(P.regex(r"(\s)*;"))
given = P.many1(P.joint(select.skip(P.spaces()), table.skip(P.spaces())))

def dbtest(connection):
    # TODO: Add a function to `db` that calls the appropriate `*_schemas` based
    #       on `type(connection)`.
    schemas = {s.table: s for s in sqlite_schemas(connection)}

    def decorate(f):
        # TODO: Ensure that `dedent(__doc__).strip()` is what we want.
        # TODO: Then.
        given_, when_ = textwrap.dedent(f.__doc__).strip().split("\n\n")
        given_ = given.parse_strict(given_)

        placeholders = {}

        rows = {s: [] for s in schemas.values()}
        for table, rows_ in given_:
            # TODO: Error if table is repeated. Implied by `SELECT *`.
            schema = schemas[table]
            rows[schema], placeholders = expand(schema, rows_, placeholders)

        rows, placeholders = references(rows, placeholders)

        @wraps(f)
        def run():
            # TODO: Truncate table before insert. Implied by `SELECT *`.
            try:
                # TODO: Skip the test if the given fails. There should
                #       be a failing test that covers the problem
                #       elsewhere.
                insert(connection, rows)

                # TODO: Actually parse, or at least split on semicolons.
                statements = when_.split("\n")
                results = []
                for statement in statements:
                    results.append(list(connection.execute(statement)))

                f(*results, **{k[1:]: v for k, v in placeholders.items()})
            finally:
                connection.rollback()

        return run
    return decorate

if __name__ == "__main__":
    import sqlite3

    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS |
                                doctest.NORMALIZE_WHITESPACE |
                                doctest.REPORT_NDIFF)
