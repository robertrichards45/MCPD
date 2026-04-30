# Caddy CAC Setup

This app does not validate CAC certificates itself. Caddy must terminate TLS, require a client certificate, verify it against your trusted issuing CA, and then forward the verified identity to Flask in `X-Authenticated-User`.

For true browser-to-origin CAC certificate auth on `mclbpd.com`, do not put a Cloudflare Access login page in front of this hostname. The client-certificate handshake must reach the origin service that is running Caddy.

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

## Caddyfile

Use [Caddyfile.example](/C:/Users/rober/Desktop/mcpd-portal/deploy/Caddyfile.example) as the starting point.

Place these files on the live Windows host:

- `C:\certs\cac-chain.pem` : trusted DoD/Federal CAC issuer chain used to validate client certificates

Caddy can obtain and renew the public TLS certificate for `mclbpd.com` automatically as long as:

- `mclbpd.com` points to your public IP
- port `443` reaches the Windows host running Caddy

Key behavior:
- `client_auth` with `require_and_verify` forces a client certificate and validates it against your CA bundle.
- `header_up -X-Authenticated-User` and `header_up -X-Authenticated-Name` strip spoofed client-supplied headers.
- `header_up X-Authenticated-User {tls_client_subject}` forwards the verified certificate subject.
- The app extracts the `CN=` portion of the certificate subject and uses that as the CAC username.

## Username Matching

With the current app logic:
- A subject like `CN=LAST.FIRST.MI.1234567890,OU=...` becomes `LAST.FIRST.MI.1234567890`
- If `CAC_AUTO_REGISTER=1`, the first successful CAC login creates the user automatically
- If `CAC_AUTO_REGISTER=0`, create the user in advance with the same username format

## Start Caddy

Example:

```powershell
caddy run --config C:\Users\rober\Desktop\mcpd-portal\deploy\Caddyfile.example
```

Or use the included launcher:

```powershell
C:\Users\rober\Desktop\mcpd-portal\deploy\run_caddy_prod_cac.cmd
```

## Validate

1. Start the Flask app on `127.0.0.1:5055`
2. Start Caddy
3. Browse to `https://mclbpd.com`
4. Insert CAC and complete the client-certificate prompt
5. Use `Create Account with CAC` on first sign-in, then `CAC Login` after the account exists

## Notes

- The Flask app should not be exposed directly to the internet when using this setup
- If your cert subject format is different, adjust user provisioning to match what Caddy forwards
- If you need a different identity field than the subject CN, change the proxy header mapping and set `CAC_USERNAME_HEADERS` accordingly
- Keep public self-registration disabled for CAC-only deployments; admins can still create users manually from the admin panel when needed
- Government clients will only trust this cleanly when `mclbpd.com` presents a real public TLS certificate. In this setup, Caddy obtains that certificate automatically from a public CA.
- For real CAC client-certificate auth through Cloudflare DNS, use DNS-only (gray cloud) for `mclbpd.com` so the browser connects directly to the origin TLS service
