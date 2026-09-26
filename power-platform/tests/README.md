# Pre-tenant validation

Run from the repository root:

```powershell
python power-platform/tests/validate_schema.py
python power-platform/tests/test_data_contracts.py
python power-platform/tests/validate_portability.py
node --check power-platform/prototype/app.js
```

These checks validate source definitions and synthetic preview behavior. They do not replace Microsoft Solution Checker, Dataverse security testing, Power BI row-level-security testing, records-management review, or government authorization.
