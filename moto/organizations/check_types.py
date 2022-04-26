from dataclasses import dataclass
from typing import Any, Callable, Optional, TypedDict, cast, Type
from pytest import Metafunc, fail
import inspect
from mypy_boto3_organizations import OrganizationsClient
from moto.organizations.models import OrganizationsBackend

AnyCallable = Callable[..., Any]


@dataclass
class APIPair:
    model_api: Optional[AnyCallable]
    boto3_api: AnyCallable


def pytest_generate_tests(metafunc: Metafunc) -> None:
    api_names = [name for name in dir(OrganizationsClient) if not name.startswith("_")]
    api_pairs = [_pair_model_and_boto3_apis(name) for name in api_names]
    metafunc.parametrize("pair", api_pairs, ids=api_names)


def _pair_model_and_boto3_apis(api_name: str) -> APIPair:
    return APIPair(
        model_api=cast(AnyCallable, getattr(OrganizationsBackend, api_name, None)),
        boto3_api=cast(AnyCallable, getattr(OrganizationsClient, api_name)),
    )


def test_model_mimics_boto3_api_return_type_name(pair: APIPair) -> None:
    if pair.model_api is None:
        fail("Model API not implemented.")

    model_return_type = get_return_type(pair.model_api)
    boto3_return_type = get_return_type(pair.boto3_api)
    assert model_return_type.__name__ == boto3_return_type.__name__


def test_model_returns_all_keys_except_response_metadata_and_next_token(
    pair: APIPair,
) -> None:
    if pair.model_api is None:
        fail("Model API not implemented.")

    model_return_type = get_return_type(pair.model_api)
    boto3_return_type = get_return_type(pair.boto3_api)

    ignored_keys = ["ResponseMetadata", "NextToken"]
    boto3_required_keys = {
        k for k in boto3_return_type.__required_keys__ if k not in ignored_keys  # type: ignore[attr-defined]
    }

    assert model_return_type.__required_keys__ == boto3_required_keys  # type: ignore[attr-defined]


def get_return_type(func: AnyCallable) -> Type[TypedDict]:  # type: ignore[valid-type]
    return cast(Type[TypedDict], inspect.getfullargspec(func).annotations["return"])  # type: ignore[valid-type]
