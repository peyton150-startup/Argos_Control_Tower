def test_backend_package_imports() -> None:
    import app

    assert app.__doc__ == "Argos Control Tower backend."
