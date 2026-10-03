import re

from tests.conftest import generate_test_schema_name


def test_generate_test_schema_name_uses_test_prefix() -> None:
    schema_name = generate_test_schema_name()

    assert schema_name.startswith("test_")
    assert re.fullmatch(r"test_[a-z0-9_]+", schema_name) is not None
