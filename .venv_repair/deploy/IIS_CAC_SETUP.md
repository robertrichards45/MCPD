# IIS CAC Setup

This app expects IIS to complete the certificate check first, then pass the authenticated identity to Flask in `X-Authenticated-User`.

## Recommended IIS Pattern

Use IIS as the HTTPS front end and reverse proxy:
- Enable client certificate authentication on the IIS site
- Use IIS client certificate mapping authentication or another mapping method so IIS resolves the cert to an authenticated Windows identity
- Add a URL Rewrite rule that proxies to `http://127.0.0.1:5055`
- Add a custom request header so Flask receives the mapped identity

The important point is that Flask should receive a trusted username, not a raw untrusted header from the browser.

## Windows Features

Install:
- Web Server (IIS)
- Request Routing
- URL Rewrite
- Client Certificate Mapping Authentication

## App Settings

Set these in `.env`:

```env
APP_ENV=prod
APP_DOMAIN=mclbpd.com
PREFERRED_URL_SCHEME=https
SESSION_COOKIE_SECURE=1
CAC_AUTH_ENABLED=1
CAC_AUTO_REGISTER=1
CAC_DEBUG_ENABLED=0
PUBLIC_SELF_REGISTER_ENABLED=0
CAC_USERNAME_HEADER=X-Authenticated-User
CAC_NAME_HEADER=X-Authenticated-Name
```

## IIS Site Authentication

For the public site:
- Disable Anonymous Authentication if your CAC policy requires certificate auth before access
- Enable Client Certificate Mapping Authentication
- Configure the certificate mapping so an approved CAC cert maps to a Windows user

Once mapped, IIS can expose that resolved account as a server variable such as `LOGON_USER`.

## Reverse Proxy Rule

Enable ARR proxying and add a reverse proxy rule to `http://127.0.0.1:5055`.

In the same rule, set server variables / request headers so the backend receives:
- `X-Authenticated-User: {LOGON_USER}`
- `X-Authenticated-Name: {LOGON_USER}`

If your environment exposes a different resolved identity variable, use that instead of `LOGON_USER`.

## Example web.config

Use [web.config.example](/C:/Users/rober/Desktop/mcpd-portal/deploy/web.config.example) as the starting point.

It:
- Allows IIS to set the `HTTP_X_AUTHENTICATED_USER` and `HTTP_X_AUTHENTICATED_NAME` server variables
- Copies `LOGON_USER` into those headers for the backend request
- Rewrites all traffic to the Flask app at `127.0.0.1:5055`

## Validate

1. Start the Flask app locally on `127.0.0.1:5055`
2. Restart IIS after applying the site changes
3. Browse to the IIS site over HTTPS
4. Complete the CAC certificate prompt
5. Use `Create Account with CAC` for first-time users, then `CAC Login` afterward

## Notes

- Do not trust browser-supplied `X-Authenticated-User` headers directly
- If IIS is only forwarding the raw certificate blob (`X-ARR-ClientCert`), the app will not use that by default
- The clean path is to have IIS map the cert to a resolved identity and forward that identity header to Flask
- Leave public self-registration disabled for normal users and use the admin panel only for exceptional manual account creation
