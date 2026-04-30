# Cloudflare Checklist For `mclbpd.com`

This checklist is specific to the current MCPD Portal repo and startup scripts.

Current local wiring in this repo:

- Flask app runs on `http://127.0.0.1:8091`
- Public tunnel launcher is `launch_mclbpd_tunnel.cmd`
- Startup wrapper is `start_website.cmd`
- MCPD launcher supports either a token in `tunnels.local.cmd` or a named tunnel config file at `deploy/cloudflared-mclbpd.yml`

Relevant files:

- `launch_mclbpd_tunnel.cmd`
- `start_website.cmd`
- `app.py`
- `deploy/MCEN_EDGE_CHECKLIST.md`

## Current State Confirmed From Repo

The repo currently expects:

- local app origin: `http://127.0.0.1:8091`
- a Cloudflare tunnel for `mclbpd.com`
- Cloudflare to sit in front of the origin

Important security note:

- older versions of this repo stored tunnel tokens in launcher scripts
- treat those older tokens as exposed
- rotate them in Cloudflare Zero Trust and store replacements only in `tunnels.local.cmd` or the process environment

## Part 1: Verify The Local App

Before touching Cloudflare, verify the app itself is reachable locally.

1. Run the local app launcher.
2. Confirm `http://127.0.0.1:8091` loads on the host machine.
3. Confirm the app is using production settings when intended:
   - `APP_ENV=prod`
   - `TRUST_PROXY=1`
   - `FORCE_HTTPS=1`
   - `HSTS_ENABLED=1`

If the local app is not stable on `8091`, Cloudflare will only proxy an origin failure.

## Part 2: Fix The Tunnel Secret First

Because the token is stored in a repo file, rotate it before relying on the tunnel.

In Cloudflare Zero Trust:

1. Open `Networks -> Tunnels`.
2. Find the tunnel used for `mclbpd.com`.
3. Rotate or regenerate the tunnel token.
4. Save the new token in local-only config:
   - `tunnels.local.cmd`
   - or environment variable `MCLBPD_TUNNEL_TOKEN`

Better long-term options:

- use a named tunnel config file plus credentials file
- keep the token out of the repo and inject it from environment or a local-only script

Named tunnel config path in this repo:

- copy `deploy/cloudflared-mclbpd.yml.example` to `deploy/cloudflared-mclbpd.yml`
- set the real tunnel UUID
- set the matching credentials JSON path under `%USERPROFILE%\.cloudflared`

## Part 3: Verify The Public Hostname Mapping

In Cloudflare Zero Trust:

1. Open `Networks -> Tunnels`.
2. Select the tunnel used for the MCPD portal.
3. Check `Public Hostnames`.
4. Confirm there is an entry for:
   - `mclbpd.com`
5. Confirm the service target is:
   - `http://127.0.0.1:8091`

If you also want `www`, add:

- `www.mclbpd.com -> http://127.0.0.1:8091`

The Flask app already redirects `www.mclbpd.com` to `https://mclbpd.com`.

## Part 4: Verify DNS Proxying

In the Cloudflare DNS dashboard:

1. Find the `mclbpd.com` DNS record.
2. Confirm it is proxied through Cloudflare, not DNS-only.
3. If `www.mclbpd.com` exists, confirm it is also proxied.

Goal:

- MCEN and public clients should see Cloudflare as the public edge, not the origin host directly.

## Part 5: Enforce HTTPS At The Edge

In Cloudflare Dashboard:

1. Go to `SSL/TLS -> Overview`.
2. Set mode to `Full`.
   Use `Full (strict)` if your origin-side certificate setup supports it.

Then:

1. Go to `SSL/TLS -> Edge Certificates`.
2. Enable `Always Use HTTPS`.
3. Enable `Automatic HTTPS Rewrites`.
4. Set minimum TLS version to `1.2`.

This is the critical fix for the MCEN block page showing `http://mclbpd.com`.

## Part 6: Add Or Confirm Redirect Behavior

Preferred result:

- `http://mclbpd.com/*` -> `https://mclbpd.com/*`
- `https://www.mclbpd.com/*` -> `https://mclbpd.com/*`

Recommended approach:

- let Cloudflare force HTTP to HTTPS
- let Flask handle `www` to apex redirect

Optional:

- add a Cloudflare redirect rule for `www` to apex if you want that redirect to happen before the request reaches Flask

## Part 7: Confirm Security Headers

The app already sets these headers:

- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `Cross-Origin-Opener-Policy`
- `Strict-Transport-Security` on HTTPS responses

You do not need to recreate them in Cloudflare unless you want edge-level duplication.

If you do add edge headers, keep them aligned with the app to avoid inconsistent behavior.

## Part 8: Keep The Tunnel Up

The repo startup wrapper currently launches:

- the local portal
- the vet tunnel
- the MCPD portal tunnel

Files involved:

- `start_website.cmd`
- `launch_local.cmd`
- `launch_vet_tunnel.cmd`
- `launch_mclbpd_tunnel.cmd`

Requirements:

- the Flask app must stay up on `8091`
- the `mclbpd.com` tunnel must stay connected

If Cloudflare scans the hostname while the tunnel is down, the domain can look unstable or suspicious.

## Part 9: Validate From Outside The Host

From a non-MCEN network, confirm:

1. `http://mclbpd.com` redirects immediately to HTTPS
2. `https://mclbpd.com` loads cleanly
3. `https://www.mclbpd.com` lands on `https://mclbpd.com`
4. `https://mclbpd.com/sitemap.xml` loads
5. No certificate warnings appear

If all of those pass, the remaining issue is likely MCEN categorization rather than app misconfiguration.

## Part 10: If MCEN Still Blocks It

If the site is fully HTTPS-only and stable behind Cloudflare but MCEN still shows `Suspicious`:

- the domain likely needs time for recategorization
- a waiver or formal recategorization path may still be required

Use the MCEN-specific checklist here:

- `deploy/MCEN_EDGE_CHECKLIST.md`

## Recommended Final Configuration For This Repo

- Cloudflare proxied hostname for `mclbpd.com`
- Cloudflare Tunnel public hostname pointing to `http://127.0.0.1:8091`
- `Always Use HTTPS` enabled
- minimum TLS `1.2`
- local app running continuously on port `8091`
- rotated tunnel token not stored in plaintext in the repo
