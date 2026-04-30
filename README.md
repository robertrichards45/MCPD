# MCPD Internal Portal

## Setup
1. Install Python 3.10+
2. Create venv and install requirements:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create `.env` from `.env.example` and set `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
   For reverse-proxy deployments (IIS/Caddy), also set `TRUST_PROXY=1`.
4. Run:
   ```bash
   python app.py
   ```
5. Visit `http://localhost:5055`

## Admin Bootstrap
Admin user is auto-created at startup from:
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

## CAC Login
- Enable with `CAC_AUTH_ENABLED=1`
- Optional auto-provisioning: `CAC_AUTO_REGISTER=1`
- Optional header inspection endpoint: `CAC_DEBUG_ENABLED=1`
- Public username/password self-registration can be disabled with `PUBLIC_SELF_REGISTER_ENABLED=0` (recommended for CAC-only deployments)
- The app expects an upstream proxy or access layer to terminate CAC auth and forward the authenticated user in one of the configured username headers (`CAC_USERNAME_HEADERS`)
- Default supported username headers include `X-Authenticated-User`, `X-Client-Cert-Subject`, `X-SSL-Client-S-DN`, `X-ARR-ClientCert-Subject`, `Cf-Access-Authenticated-User-Email`, and `Cf-Access-Email`
- Default supported display-name headers include `X-Authenticated-Name`, `X-Client-Cert-Subject`, `X-SSL-Client-S-DN`, `X-ARR-ClientCert-Subject`, `Cf-Access-Authenticated-User-Name`, and `Cf-Access-Name`
- For IIS/Caddy/Cloudflare deployments, set `TRUST_PROXY=1` so Flask respects forwarded host/protocol headers
- Recommended production posture: `CAC_AUTH_ENABLED=1`, `CAC_AUTO_REGISTER=1`, `PUBLIC_SELF_REGISTER_ENABLED=0`

## Modules
- Dashboard with CLEO, Forms, Training, Stats, Annual AI
- Forms upload/download (admin upload)
- Training rosters: upload PDF, sign with signature pad, download compiled PDF
- Stats: upload Excel to update officer stats (April–April)
- Annual AI: ask questions (needs `OPENAI_API_KEY`)

## Excel Upload Layouts
Layout A:
- Columns: `Officer`, `Category`, `Value`

Layout B:
- First column: `Officer`
- Remaining columns: category names

## Add New Pages
Add a route in `app/routes`, a template in `app/templates`, and link it in the nav.

