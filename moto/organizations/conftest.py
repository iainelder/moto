import inspect
from typing import Any, Callable, Type, TypedDict, cast
from pytest import Metafunc
from mypy_boto3_organizations import OrganizationsClient


AnyCallable = Callable[..., Any]

# For whatever reason TypedDict is not a valid return type according to mypy.
# But as far as I know it is the abstract type that implements the
# __required_keys__ property used in tests.
def get_return_type(func: AnyCallable) -> Type[TypedDict]:  # type: ignore[valid-type]
    sig = inspect.signature(func)
    return cast(Type[TypedDict], sig.return_annotation)  # type: ignore[valid-type]


# These client helper functions are not a wrapper of a public API. They are
# listed so that they can be ignored when searching for the functions that wrap
# public APIs.
#
# TODO: Is get_paginator and can_paginate a feature of all boto3 clients? If
# they are, why are they not part of the BaseClient?
CLIENT_HELPER_FUNCTIONS = frozenset([
    "get_paginator",
    "can_paginate",
    "generate_presigned_url",
])

# Read __dict__ to avoid the members of superclass BaseClient. These are helper
# methods and properties and never public APIs.
BOTO3_APIS = {
    k: v
    for k, v in OrganizationsClient.__dict__.items()
    if callable(v) and k not in CLIENT_HELPER_FUNCTIONS
}

NON_RETURNING_APIS = {k: v for k, v in BOTO3_APIS.items() if get_return_type(v) is None}

RETURNING_APIS = {k: v for k, v in BOTO3_APIS.items() if get_return_type(v) is not None}


def pytest_generate_tests(metafunc: Metafunc) -> None:
    test_name = metafunc.function.__name__

    if "api" in metafunc.fixturenames:
        metafunc.parametrize(
            "api",
            BOTO3_APIS.values(),
            ids=BOTO3_APIS.keys()
        )
        return

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
