import re


class BaseDao:
    def validate_table_name(self, table_name: str) -> None:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name) is None:
            msg = """
            Table names must start with a letter or underscore and
            contain only letters, numbers, and underscores.
            """
            raise ValueError(msg)
