"""Why the seed stopped before writing anything."""


class SeedRefused(Exception):
    """The seed will not run as asked (unsafe in production, or the database is not empty).

    The message says what to change. It never contains a password or token.
    """
