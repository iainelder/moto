from pprint import pprint
import inspect

from mypy_boto3_organizations import OrganizationsClient
from .models import OrganizationsBackend

boto3_function = OrganizationsClient.create_organization
moto_function = OrganizationsBackend.create_organization

pprint(inspect.getfullargspec(boto3_function))
pprint(inspect.getfullargspec(moto_function))

# TODO: add pytest tests to check that the patched type and the original type are the same except for the ResponseMetadata key
# TODO: add pytest tests to check that the backend methods have the same signature as the original client
# Use pytest's metafunc for this
