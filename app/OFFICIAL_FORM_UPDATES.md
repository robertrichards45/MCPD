# Official Form Updates

Last updated: 2026-04-30

## DSO / DLA Status

- DLA/NFOL now points users to DSO / Navy Digital Storefront for physical and digital forms.
- DSO is a storefront application. If it returns a login, CAC, or SmartStore page instead of a direct PDF, MCPD Portal will mark the source as gated and will not replace the local form.
- Direct official PDFs from allowed official hosts can be tracked and applied.

## Supported Auto-Update Flow

1. Open `Forms Manager`.
2. Select a form.
3. Add the direct official PDF URL in `Official PDF URL`.
4. Add the edition/version label if known.
5. Enable `Allow scheduled official-source auto update`.
6. Click `Check Official Source` to verify.
7. Click `Apply Official Update` to replace the local form if a different official PDF is available.

## Scheduled Check

Run from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\check_form_source_updates.py --apply
```

The script only updates forms that have auto-update enabled and an official direct PDF URL configured.

## Safety Rules

- Only HTTPS URLs are allowed.
- Only official hosts are allowed: DSO/DLA, DLA Forms, DONI/SECNAV, and WHS/ESD.
- Returned content must be a real PDF.
- HTML/login/storefront pages are rejected.
- The current form is replaced only when the official PDF hash differs from the local file.

