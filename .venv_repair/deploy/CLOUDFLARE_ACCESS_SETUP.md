# Cloudflare Access Temporary External Login

This is the fastest way to expose the site online before full CAC is in place.

Cloudflare Access authenticates the user at the edge, then forwards trusted identity headers to the Flask app. The app already supports Cloudflare Access header names by default.

## What This Gives You

- Public HTTPS URL in front of the local app
- Cloudflare-managed login instead of direct CAC certificate handling
- User identity forwarded in headers such as `Cf-Access-Authenticated-User-Email`

This is a temporary external access path, not real CAC smart-card authentication.

If you want real CAC certificate auth on `mclbpd.com`, do not use this Access application on that hostname.

## App Settings

Set these in `.env`:

```env
APP_ENV=prod
PREFERRED_URL_SCHEME=https
SESSION_COOKIE_SECURE=1
CAC_AUTH_ENABLED=1
CAC_AUTO_REGISTER=1
CAC_DEBUG_ENABLED=0
PUBLIC_SELF_REGISTER_ENABLED=0
CAC_USERNAME_HEADERS=X-Authenticated-User,Cf-Access-Authenticated-User-Email,Cf-Access-Email
CAC_NAME_HEADERS=X-Authenticated-Name,Cf-Access-Authenticated-User-Name,Cf-Access-Name
```

The default config already includes the Cloudflare Access headers above, so in most cases you only need `CAC_AUTH_ENABLED=1`.

## Cloudflare Access Flow

1. Add your domain to Cloudflare.
2. Open the Cloudflare Zero Trust dashboard.
3. Go to `Networks` -> `Tunnels`.
4. Create a named tunnel.
5. Install or connect `cloudflared` on the machine running the Flask app.
6. Point the tunnel public hostname to `http://127.0.0.1:5055`.
7. Go to `Access` -> `Applications`.
8. Create a Self-hosted application for the same hostname.
9. Add an Access policy that allows the users you want.
10. Verify the Access application is actually attached to the hostname before testing.

Once Access is in front of the hostname, Cloudflare injects the identity headers after successful login.

If the app shows `CAC identity header was not provided...` on `https://mclbpd.com`, Cloudflare proxying is on but Access is not injecting identity yet. Orange-cloud proxying by itself does not add the required user headers.

## Temporary Local Tunnel Command

If you just want a quick test and already have `cloudflared` installed:

```powershell
cloudflared tunnel --url http://127.0.0.1:5055 --no-autoupdate
```

That creates a temporary `trycloudflare.com` URL. For controlled login policies, use a named tunnel plus an Access application instead of a quick tunnel.

## Username Matching

The app normalizes values before matching users:

- `person@example.mil` becomes `person`
- `DOMAIN\person` becomes `person`

With `CAC_AUTO_REGISTER=1`, the first successful Access-backed login creates a local app user automatically.

## Validate

1. Start the Flask app locally.
2. Start the Cloudflare tunnel.
3. Open the public hostname protected by Cloudflare Access.
4. Complete the Cloudflare Access login flow.
5. Use `Create Account with CAC` for first-time users, then `CAC Login`.

The app will read the Cloudflare identity header and treat it as the upstream-authenticated user.

## Notes

- Do not expose the Flask dev server directly to the internet without a proxy/tunnel in front of it
- Quick tunnels are for testing, not a stable production endpoint
- If your Cloudflare tenant uses a different header shape, use `CAC_DEBUG_ENABLED=1` briefly to inspect what the app receives
