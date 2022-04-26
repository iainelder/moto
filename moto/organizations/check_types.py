from .conftest import AnyCallable, get_return_type
from typing import cast
from pytest import fail
from moto.organizations.models import OrganizationsBackend


def test_model_returns_none(non_returning_api: AnyCallable) -> None:
    boto3_api = non_returning_api
    model_api = cast(
        AnyCallable, getattr(OrganizationsBackend, boto3_api.__name__, None)
    )

    if model_api is None:
        fail("Model API not implemented.")

    model_return_type = get_return_type(model_api)
    boto3_return_type = get_return_type(boto3_api)
    assert model_return_type is None and boto3_return_type is None


def test_model_mimics_boto3_api_return_type_name(returning_api: AnyCallable) -> None:
    boto3_api = returning_api
    model_api = cast(
        AnyCallable, getattr(OrganizationsBackend, boto3_api.__name__, None)
    )

    if model_api is None:
        fail("Model API not implemented.")

    model_return_type = get_return_type(model_api)
    boto3_return_type = get_return_type(boto3_api)
    assert model_return_type.__name__ == boto3_return_type.__name__


def test_model_returns_all_keys_except_response_metadata_and_next_token(
    returning_api: AnyCallable,
) -> None:
    boto3_api = returning_api
    model_api = cast(
        AnyCallable, getattr(OrganizationsBackend, boto3_api.__name__, None)
    )

    if model_api is None:
        fail("Model API not implemented.")

    model_return_type = get_return_type(model_api)
    boto3_return_type = get_return_type(boto3_api)

    ignored_keys = ["ResponseMetadata", "NextToken"]
    boto3_required_keys = {
        k for k in boto3_return_type.__required_keys__ if k not in ignored_keys  # type: ignore[attr-defined]
    }

    assert model_return_type.__required_keys__ == boto3_required_keys  # type: ignore[attr-defined]
