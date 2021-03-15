import decimal
import re

from jschon.json import JSON
from jschon.jsonschema import Keyword, Scope, JSONSchema
from jschon.utils import tuplify

__all__ = [
    'TypeKeyword',
    'EnumKeyword',
    'ConstKeyword',
    'MultipleOfKeyword',
    'MaximumKeyword',
    'ExclusiveMaximumKeyword',
    'MinimumKeyword',
    'ExclusiveMinimumKeyword',
    'MaxLengthKeyword',
    'MinLengthKeyword',
    'PatternKeyword',
    'MaxItemsKeyword',
    'MinItemsKeyword',
    'UniqueItemsKeyword',
    'MaxContainsKeyword',
    'MinContainsKeyword',
    'MaxPropertiesKeyword',
    'MinPropertiesKeyword',
    'RequiredKeyword',
    'DependentRequiredKeyword',
]


class TypeKeyword(Keyword):
    __keyword__ = "type"
    __schema__ = {
        "anyOf": [
            {"enum": ["null", "boolean", "number", "integer", "string", "array", "object"]},
            {
                "type": "array",
                "items": {"enum": ["null", "boolean", "number", "integer", "string", "array", "object"]},
                "minItems": 1,
                "uniqueItems": True
            }
        ]
    }

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        types = tuplify(self.json.value)
        if instance.type in types:
            valid = True
        elif instance.type == "number" and "integer" in types:
            valid = instance.value == int(instance.value)
        else:
            valid = False

        if not valid:
            scope.fail(instance, f"The instance must be of type {self.json}")


class EnumKeyword(Keyword):
    __keyword__ = "enum"
    __schema__ = {"type": "array", "items": True}

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if instance not in self.json:
            scope.fail(instance, f"The value must be one of {self.json}")


class ConstKeyword(Keyword):
    __keyword__ = "const"
    __schema__ = True

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if instance != self.json:
            scope.fail(instance, f"The value must be equal to {self.json}")


class MultipleOfKeyword(Keyword):
    __keyword__ = "multipleOf"
    __schema__ = {"type": "number", "exclusiveMinimum": 0}
    __types__ = "number"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        try:
            if instance % self.json != 0:
                scope.fail(instance, f"The value must be a multiple of {self.json}")
        except decimal.InvalidOperation:
            scope.fail(instance, f"Invalid operation: {instance} % {self.json}")


class MaximumKeyword(Keyword):
    __keyword__ = "maximum"
    __schema__ = {"type": "number"}
    __types__ = "number"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if instance > self.json:
            scope.fail(instance, f"The value may not be greater than {self.json}")


class ExclusiveMaximumKeyword(Keyword):
    __keyword__ = "exclusiveMaximum"
    __schema__ = {"type": "number"}
    __types__ = "number"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if instance >= self.json:
            scope.fail(instance, f"The value must be less than {self.json}")


class MinimumKeyword(Keyword):
    __keyword__ = "minimum"
    __schema__ = {"type": "number"}
    __types__ = "number"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if instance < self.json:
            scope.fail(instance, f"The value may not be less than {self.json}")


class ExclusiveMinimumKeyword(Keyword):
    __keyword__ = "exclusiveMinimum"
    __schema__ = {"type": "number"}
    __types__ = "number"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if instance <= self.json:
            scope.fail(instance, f"The value must be greater than {self.json}")


class MaxLengthKeyword(Keyword):
    __keyword__ = "maxLength"
    __schema__ = {"type": "integer", "minimum": 0}
    __types__ = "string"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if len(instance) > self.json:
            scope.fail(instance, f"The text is too long (maximum {self.json} characters)")


class MinLengthKeyword(Keyword):
    __keyword__ = "minLength"
    __schema__ = {"type": "integer", "minimum": 0, "default": 0}
    __types__ = "string"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if len(instance) < self.json:
            scope.fail(instance, f"The text is too short (minimum {self.json} characters)")


class PatternKeyword(Keyword):
    __keyword__ = "pattern"
    __schema__ = {"type": "string", "format": "regex"}
    __types__ = "string"

    def __init__(self, parentschema: JSONSchema, value: str):
        super().__init__(parentschema, value)
        self.regex = re.compile(value)

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if self.regex.search(instance.value) is None:
            scope.fail(instance, f"The text must match the regular expression {self.json}")


class MaxItemsKeyword(Keyword):
    __keyword__ = "maxItems"
    __schema__ = {"type": "integer", "minimum": 0}
    __types__ = "array"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if len(instance) > self.json:
            scope.fail(instance, f"The array has too many elements (maximum {self.json})")


class MinItemsKeyword(Keyword):
    __keyword__ = "minItems"
    __schema__ = {"type": "integer", "minimum": 0, "default": 0}
    __types__ = "array"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if len(instance) < self.json:
            scope.fail(instance, f"The array has too few elements (minimum {self.json})")


class UniqueItemsKeyword(Keyword):
    __keyword__ = "uniqueItems"
    __schema__ = {"type": "boolean", "default": False}
    __types__ = "array"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if not self.json.value:
            return

        uniquified = []
        for item in instance:
            if item not in uniquified:
                uniquified += [item]

        if len(instance) > len(uniquified):
            scope.fail(instance, "The array's elements must all be unique")


class MaxContainsKeyword(Keyword):
    __keyword__ = "maxContains"
    __schema__ = {"type": "integer", "minimum": 0}
    __types__ = "array"
    __depends__ = "contains"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if contains := scope.sibling("contains"):
            if (contains_annotation := contains.annotations.get("contains")) and \
                    contains_annotation.value > self.json:
                scope.fail(instance,
                           'The array has too many elements matching the '
                           f'"contains" subschema (maximum {self.json})')


class MinContainsKeyword(Keyword):
    __keyword__ = "minContains"
    __schema__ = {"type": "integer", "minimum": 0, "default": 1}
    __types__ = "array"
    __depends__ = "contains", "maxContains"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if contains := scope.sibling("contains"):
            contains_count = contains_annotation.value \
                if (contains_annotation := contains.annotations.get("contains")) \
                else 0

            valid = contains_count >= self.json

            if valid and not contains.valid:
                max_contains = scope.sibling("maxContains")
                if not max_contains or max_contains.valid:
                    contains.errors.clear()

            if not valid:
                scope.fail(instance,
                           'The array has too few elements matching the '
                           f'"contains" subschema (minimum {self.json})')


class MaxPropertiesKeyword(Keyword):
    __keyword__ = "maxProperties"
    __schema__ = {"type": "integer", "minimum": 0}
    __types__ = "object"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if len(instance) > self.json:
            scope.fail(instance, f"The object has too many properties (maximum {self.json})")


class MinPropertiesKeyword(Keyword):
    __keyword__ = "minProperties"
    __schema__ = {"type": "integer", "minimum": 0, "default": 0}
    __types__ = "object"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        if len(instance) < self.json:
            scope.fail(instance, f"The object has too few properties (minimum {self.json})")


class RequiredKeyword(Keyword):
    __keyword__ = "required"
    __schema__ = {
        "type": "array",
        "items": {"type": "string"},
        "uniqueItems": True,
        "default": []
    }
    __types__ = "object"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        missing = [name for name in self.json if name.value not in instance]
        if missing:
            scope.fail(instance, f"The object is missing required properties {missing}")


class DependentRequiredKeyword(Keyword):
    __keyword__ = "dependentRequired"
    __schema__ = {
        "type": "object",
        "additionalProperties": {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True,
            "default": []
        }
    }
    __types__ = "object"

    def evaluate(self, instance: JSON, scope: Scope) -> None:
        missing = {}
        for name, dependents in self.json.items():
            if name in instance:
                missing_deps = [dep for dep in dependents if dep.value not in instance]
                if missing_deps:
                    missing[name] = missing_deps

        if missing:
            scope.fail(instance, f"The object is missing dependent properties {missing}")