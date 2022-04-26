# Organizations

Generate types without ResourceMetadata and NextToken keys:

```bash
python moto/organizations/write_type_defs.py
```

References:

* https://stackoverflow.com/questions/11303225/how-to-remove-multiple-indexes-from-a-list-at-the-same-time
* https://stackoverflow.com/questions/57652922/is-it-possible-to-call-black-as-an-api

TypedDict accepts only dict literals, and you can't define subtractive types.

https://stackoverflow.com/questions/66396842/why-can-a-final-dictionary-not-be-used-as-a-literal-in-typeddict

So the best solution I have found is to copy the type defs from the original
package and strip them of the ResponseMetadata keys.

This should be run whenever the version of boto3 changes. Or whenever the module
needs new types.

Test that the backend types match the boto3 API:

```bash
pytest moto/organizations/check_types.py
```

References:

* https://medium.com/opsops/deepdive-into-pytest-parametrization-cb21665c05b9
