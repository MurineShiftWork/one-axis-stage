import importlib.metadata


def test_version_is_non_empty_string() -> None:
    version = importlib.metadata.version("one-axis-stage")
    assert isinstance(version, str)
    assert version
