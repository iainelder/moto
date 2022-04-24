from pathlib import Path
import ast
from astunparse import unparse as ast_unparse  # type: ignore[import]
import black
from inspect import getsource
import mypy_boto3_organizations.type_defs
from typing import Iterable, cast
from types import ModuleType


def main() -> None:
    tree = parse_module(mypy_boto3_organizations.type_defs)
    del_from_all_dict_nodes(tree, keys=["NextToken", "ResponseMetadata"])
    replace_relative_import(
        tree, relative="literals", absolute="mypy_boto3_organizations.literals"
    )
    new_source = reformat(tree)
    Path("moto/organizations/type_defs.py").write_text(new_source)


def parse_module(module: ModuleType) -> ast.AST:
    source = getsource(module)
    return ast.parse(source)


def del_from_all_dict_nodes(tree: ast.AST, *, keys: Iterable[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            del_from_dict_node(node, keys)


def del_from_dict_node(node: ast.Dict, keys: Iterable[str]) -> None:
    # This would have been a list comprehension, but mypy requires casts that
    # made it ugly.
    items_to_delete = list(iter_indexes_to_delete(node, keys))
    # Go backwards to avoid deleting the wrong thing or failing with an IndexError.
    # Deletion reindexes subsequent nodes.
    for i in reversed(items_to_delete):
        del node.keys[i]
        del node.values[i]


def iter_indexes_to_delete(node: ast.Dict, keys: Iterable[str]) -> Iterable[int]:
    for i, k in enumerate(node.keys):
        const = cast(ast.Constant, k)
        if cast(str, const.value) in keys:
            yield i


def replace_relative_import(tree: ast.AST, *, relative: str, absolute: str) -> None:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module == relative
        ):
            node.level = 0
            node.module = absolute
            break


def reformat(tree: ast.AST) -> str:
    return black.format_file_contents(
        src_contents=ast_unparse(tree), fast=False, mode=black.FileMode()
    )


if __name__ == "__main__":
    main()
