"""Level 0: Schema 子集与参数校验。"""

import pytest

from tools.schema import (
    SchemaDefinitionError,
    validate_arguments,
    validate_schema,
)


def echo_schema():
    return {
        "type": "object",
        "properties": {"text": {"type": "string", "maxLength": 10}},
        "required": ["text"],
        "additionalProperties": False,
    }


class TestValidateSchema:
    def test_accepts_subset_schema(self):
        validate_schema(echo_schema())

    def test_rejects_non_object_root(self):
        with pytest.raises(SchemaDefinitionError):
            validate_schema({"type": "string"})

    def test_rejects_open_schema(self):
        schema = echo_schema()
        schema["additionalProperties"] = True
        with pytest.raises(SchemaDefinitionError):
            validate_schema(schema)

    def test_rejects_unsupported_property_type(self):
        schema = echo_schema()
        schema["properties"]["items"] = {"type": "array"}
        with pytest.raises(SchemaDefinitionError):
            validate_schema(schema)

    def test_rejects_empty_properties(self):
        with pytest.raises(SchemaDefinitionError):
            validate_schema({"type": "object", "properties": {}, "additionalProperties": False})

    def test_rejects_unknown_required_field(self):
        schema = echo_schema()
        schema["required"] = ["text", "volume"]
        with pytest.raises(SchemaDefinitionError):
            validate_schema(schema)

    def test_rejects_non_integer_max_length(self):
        schema = echo_schema()
        schema["properties"]["text"]["maxLength"] = "10"
        with pytest.raises(SchemaDefinitionError):
            validate_schema(schema)


class TestValidateArguments:
    def test_valid_arguments_pass(self):
        assert validate_arguments({"text": "hi"}, echo_schema()) == []

    def test_missing_required_rejected(self):
        violations = validate_arguments({}, echo_schema())
        assert [v.code for v in violations] == ["missing_required"]

    def test_unknown_field_rejected(self):
        violations = validate_arguments({"text": "hi", "extra": 1}, echo_schema())
        assert [v.code for v in violations] == ["unknown_field"]

    def test_type_mismatch_rejected(self):
        violations = validate_arguments({"text": 123}, echo_schema())
        assert [v.code for v in violations] == ["type_mismatch"]

    def test_boolean_not_accepted_as_integer(self):
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}},
            "required": ["count"],
            "additionalProperties": False,
        }
        assert validate_arguments({"count": True}, schema)[0].code == "type_mismatch"
        assert validate_arguments({"count": 3}, schema) == []

    def test_max_length_enforced(self):
        violations = validate_arguments({"text": "x" * 11}, echo_schema())
        assert [v.code for v in violations] == ["too_long"]

    def test_collects_multiple_violations(self):
        violations = validate_arguments({"extra": "x"}, echo_schema())
        assert {v.code for v in violations} == {"missing_required", "unknown_field"}
