# Organizations

Generate types without ResourceMetadata keys:

```bash
cat ~/tmp/moto/lib/python3.8/site-packages/mypy_boto3_organizations/type_defs.py \
| grep -v '"ResponseMetadata": "ResponseMetadataTypeDef",' \
| sed -e 's/from .literals /from mypy_boto3_organizations.literals /' \
> moto/organizations/type_defs.py
```

TypedDict accepts only dict literals, and you can't define subtractive types.

https://stackoverflow.com/questions/66396842/why-can-a-final-dictionary-not-be-used-as-a-literal-in-typeddict

So the best solution I have found is to copy the type defs from the original
package and strip them of the ResponseMetadata keys.

This should be run whenever the version of boto3 changes. Or whenever the module
needs new types.
