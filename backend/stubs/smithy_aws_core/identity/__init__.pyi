"""Minimal stub: the real package ships no type annotations on __init__, which
trips mypy strict's no-untyped-call check at every construction site.
"""

class EnvironmentCredentialsResolver:
    def __init__(self) -> None: ...
