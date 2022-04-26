import inspect
from typing import Any, Callable, Type, TypedDict, cast
from pytest import Metafunc
from mypy_boto3_organizations import OrganizationsClient


AnyCallable = Callable[..., Any]


def get_return_type(func: AnyCallable) -> Type[TypedDict]:  # type: ignore[valid-type]
    sig = inspect.signature(func)
    return cast(Type[TypedDict], sig.return_annotation)  # type: ignore[valid-type]


# Read __dict__ to avoid the members of superclass BaseClient.
BOTO3_APIS = {
    k: v
    for k, v in OrganizationsClient.__dict__.items()
    if callable(v) and k != "get_paginator"
}

NON_RETURNING_APIS = {k: v for k, v in BOTO3_APIS.items() if get_return_type(v) is None}

RETURNING_APIS = {k: v for k, v in BOTO3_APIS.items() if get_return_type(v) is not None}


def pytest_generate_tests(metafunc: Metafunc) -> None:
    test_name = metafunc.function.__name__

    if "non_returning_api" in metafunc.fixturenames:
        metafunc.parametrize(
            "non_returning_api",
            NON_RETURNING_APIS.values(),
            ids=NON_RETURNING_APIS.keys(),
        )
        return

    if "returning_api" in metafunc.fixturenames:
        metafunc.parametrize(
            "returning_api", RETURNING_APIS.values(), ids=RETURNING_APIS.keys()
        )
        return

    raise AssertionError(f"Unhandled test {test_name}")
