"""最小 JSON Schema 子集校验器(Level 0)。

只支持本项目工具实际用到的构造:object 根、string/integer/number/boolean
属性、required、additionalProperties=false、maxLength。
Registry 注册时先校验 Schema 本身在子集内(不支持即拒绝注册),
校验失败宁可拒绝合法调用,也不放行非法调用(Fail Closed)。
"""

from __future__ import annotations

from dataclasses import dataclass

_supported_property_types = ("string", "integer", "number", "boolean")


class SchemaDefinitionError(ValueError):
    """工具声明的 Schema 超出支持的子集,注册阶段直接拒绝。"""


@dataclass(frozen=True)
class SchemaViolation:
    field: str
    code: str  # missing_required | unknown_field | type_mismatch | too_long
    message: str


def validate_schema(schema: dict) -> None:
    """校验工具参数 Schema 在支持子集内,越界抛 SchemaDefinitionError。"""
    if not isinstance(schema, dict):
        raise SchemaDefinitionError("schema must be a dict")
    if schema.get("type") != "object":
        raise SchemaDefinitionError("root schema type must be 'object'")
    if schema.get("additionalProperties") is not False:
        raise SchemaDefinitionError("additionalProperties must be false")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        raise SchemaDefinitionError("properties must be a non-empty dict")
    required = schema.get("required", [])
    if not isinstance(required, list) or not all(isinstance(r, str) for r in required):
        raise SchemaDefinitionError("required must be a list of strings")
    unknown_required = set(required) - set(properties)
    if unknown_required:
        raise SchemaDefinitionError(f"required lists unknown fields: {sorted(unknown_required)}")
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            raise SchemaDefinitionError(f"property {name!r} must be a dict")
        if prop.get("type") not in _supported_property_types:
            raise SchemaDefinitionError(
                f"property {name!r} has unsupported type {prop.get('type')!r}; "
                f"supported: {_supported_property_types}"
            )
        max_length = prop.get("maxLength")
        if max_length is not None and (not isinstance(max_length, int) or isinstance(max_length, bool)):
            raise SchemaDefinitionError(f"property {name!r} maxLength must be an integer")


def validate_arguments(arguments: dict, schema: dict) -> list[SchemaViolation]:
    """按 Schema 校验参数,返回全部违规(空列表 = 合法)。"""
    violations: list[SchemaViolation] = []
    properties = schema["properties"]
    required = schema.get("required", [])

    for name in required:
        if name not in arguments:
            violations.append(
                SchemaViolation(name, "missing_required", f"missing required field {name!r}")
            )

    for name, value in arguments.items():
        if name not in properties:
            violations.append(
                SchemaViolation(name, "unknown_field", f"unknown field {name!r}")
            )
            continue
        prop = properties[name]
        expected = prop["type"]
        if not _matches_type(value, expected):
            violations.append(
                SchemaViolation(
                    name,
                    "type_mismatch",
                    f"field {name!r} must be {expected}, got {type(value).__name__}",
                )
            )
            continue
        max_length = prop.get("maxLength")
        if max_length is not None and len(value) > max_length:
            violations.append(
                SchemaViolation(
                    name,
                    "too_long",
                    f"field {name!r} exceeds maxLength={max_length} (got {len(value)})",
                )
            )

    return violations


def _matches_type(value: object, expected: str) -> bool:
    # bool 是 int 的子类,必须先排除,否则 True 会被当成 integer 放行。
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False
