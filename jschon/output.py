from typing import Dict

from jschon.json import AnyJSONCompatible
from jschon.jsonschema import Scope

__all__ = [
    'OutputFormatter',
]


class OutputFormatter:

    @staticmethod
    def flag(scope: Scope) -> Dict[str, AnyJSONCompatible]:
        return {
            "valid": scope.valid
        }

    @staticmethod
    def basic(scope: Scope) -> Dict[str, AnyJSONCompatible]:
        def visit(node: Scope):
            if node.valid is valid:
                msgval = getattr(node, msgkey)
                if msgval is not None:
                    yield {
                        "instanceLocation": str(node.instpath),
                        "keywordLocation": str(node.path),
                        "absoluteKeywordLocation": str(node.absolute_uri),
                        msgkey: msgval,
                    }
                for child in node.iter_children():
                    yield from visit(child)

        valid = scope.valid
        msgkey = "annotation" if valid else "error"
        childkey = "annotations" if valid else "errors"

        return {
            "valid": valid,
            childkey: [result for result in visit(scope)],
        }

    @staticmethod
    def detailed(scope: Scope) -> Dict[str, AnyJSONCompatible]:
        def visit(node: Scope):
            result = {
                "instanceLocation": str(node.instpath),
                "keywordLocation": str(node.path),
                "absoluteKeywordLocation": str(node.absolute_uri),
                childkey: [visit(child) for child in node.iter_children()
                           if child.valid is valid],
            }
            if not result[childkey]:
                del result[childkey]
                msgval = getattr(node, msgkey)
                if msgval is not None:
                    result[msgkey] = msgval
            elif len(result[childkey]) == 1:
                result = result[childkey][0]

            return result

        valid = scope.valid
        msgkey = "annotation" if valid else "error"
        childkey = "annotations" if valid else "errors"

        return {
            "valid": valid,
            "instanceLocation": str(scope.instpath),
            "keywordLocation": str(scope.path),
            "absoluteKeywordLocation": str(scope.absolute_uri),
            childkey: [visit(child) for child in scope.iter_children()
                       if child.valid is valid],
        }

    @staticmethod
    def verbose(scope: Scope) -> Dict[str, AnyJSONCompatible]:
        def visit(node: Scope):
            valid = node.valid
            result = {
                "valid": valid,
                "instanceLocation": str(node.instpath),
                "keywordLocation": str(node.path),
                "absoluteKeywordLocation": str(node.absolute_uri),
            }

            msgkey = "annotation" if valid else "error"
            msgval = getattr(node, msgkey)
            if msgval is not None:
                result[msgkey] = msgval

            childkey = "annotations" if valid else "errors"
            childarr = [visit(child) for child in node.iter_children()]
            if childarr:
                result[childkey] = childarr

            return result

        return visit(scope)
