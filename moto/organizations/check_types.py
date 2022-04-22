from pprint import pprint
import inspect
from deepdiff import DeepDiff
from mypy_boto3_organizations import OrganizationsClient
from moto.organizations.models import OrganizationsBackend

boto3_function = OrganizationsClient.create_organization
moto_function = OrganizationsBackend.create_organization

boto3_spec = inspect.getfullargspec(boto3_function)
moto_spec = inspect.getfullargspec(moto_function)

# TODO: add pytest tests to check that the backend methods have the same signature as the original client
pprint(DeepDiff(boto3_spec, moto_spec))

# TODO: add pytest tests to check that the patched type and the original type are the same except for the ResponseMetadata key
import mypy_boto3_organizations.type_defs as btd
import moto.organizations.type_defs as mtd

boto_type = btd.CreateOrganizationResponseTypeDef
moto_type = mtd.CreateOrganizationResponseTypeDef

DeepDiff(boto_type.__annotations__, moto_type.__annotations__)


boto_type = btd.DescribeOrganizationResponseTypeDef
moto_type = mtd.DescribeOrganizationResponseTypeDef

DeepDiff(boto_type.__annotations__, moto_type.__annotations__)

# TODO: Use pytest's metafunc for this
