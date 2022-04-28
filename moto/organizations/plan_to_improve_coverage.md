# Improve Organiations support

## Add missing APIs

Or justify their exclusion.

* AcceptHandshake
* CancelHandshake
* CreateGovCloudAccount
* DeclineHandshake
* DeleteOrganizationalUnit
* DescribeEffectivePolicy
* EnableAllFeatures
* InviteAccountToOrganization
* LeaveOrganization
* ListHandshakesForAccount

## Fix non-compliant implementations

These implementations don't follow the spec of the public API.

* CloseAccount (fix in #5072)

## Add return type information for APIs

I have an example implementation for this as a proposal.

I need this proposal to be reviewed by someone who better understands the
constraints of the moto project. If something here is unacceptable, I will
revise the proposal.

See "Why does moto depend on boto3?" for a fundamental question that I have
about the design.

Ideal situation: annotate all the backend API with the same type declared in mypy_boto3_organizations.

Problem: The return type annotation of each boto3 client methods includes the keys ResponseMetadata in all responses. The return type annotation of a paginated API includes a NextToken key.

The backend API should not return these keys.

The ResponseMetadata key is added by the real boto3 client itself whether
calling a real AWS API or a mocked one.

The NextToken key is returned by the real AWS API, but in moto the paginate
decorator should be used to generate this (see below). The core backend API
should return a response without caring about pagination.

So we need to derive a subset of the type_defs in mypy_boto3_organizations to
check the types of all the other keys. I have implemented this using a script
that filters and rewrites the type_defs, ignoring the keys discussed above.

An alternative implementation would be to ask the mypy_boto3_organizations
maintainer to add an extra level of indirection in the typing to exclude the
ResponseMetadata key and the NextToken key. I can see how it would be feasible
for the ResponseMetadata key (because it's generated client side and not part of
the public API spec) but it seems less feasible for the NextToken key (because
it is part of the spec).

## Replace kwargs with typed parameters

Follow the types in mypy_boto3_organizations.

## Fix pagination implementation

Pagination is implemented in two different ways.

ListAccounts uses the paginate decorator. The paginate decorator forces us to
diverge from the expected return type for the backend function.

The paginate decorator is appealing for its tidiness but I would like it to be
compatible with the boto3 return types.

ListAccountCreateStatus appears to have a bespoke implementation of pagination.
This should be refactored to use the paginate decorator.

# Why does moto depend on boto3?

Why does moto depend on boto3? I count 18 instances outside of the tests and
scripts that

```
(moto) $ ack --type=python --ignore-dir "tests" --ignore-dir "scripts" --ignore-dir build -- "import boto3|from boto3" | wc -l
9
```

It depends on an old version.

```
(moto) $ grep "boto3" setup.py
    "boto3>=1.9.201",
```

The way I describe to implement types would require a dependency on the latest
boto3 version (or rather the latest mypy_boto3_organizations version, which
tracks the boto3 version) to ensure coverage of the latest actions and data
types.

Requiring the latest version might be a burden on users of the moto library.
It's unfortunate that Python doesn't support using two different versions of the
same package in the same program, at least not without some hacking of the
package namespace.

See this solution for hacking the package namespace:
https://stackoverflow.com/questions/6570635/installing-multiple-versions-of-a-package-with-pip

## TODO

Check TODO comments in models and tests.
