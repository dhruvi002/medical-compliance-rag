"""Smoke tests — verify the package is importable and core modules load."""


def test_package_importable():
    import medcomply  # noqa: F401


def test_chunker_importable():
    from medcomply import chunker  # noqa: F401


def test_audit_logger_importable():
    from medcomply import audit_logger  # noqa: F401


def test_vector_store_importable():
    from medcomply import vector_store  # noqa: F401
