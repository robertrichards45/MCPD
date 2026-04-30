# MCEN Access Checklist For `mclbpd.com`

This checklist separates what the Flask app already does from what must be configured at the edge.

The MCEN block page for March 11, 2026 showed:

- URL: `http://mclbpd.com/`
- Category: `Suspicious`

That means two things can be true at the same time:

1. The edge is still exposing or allowing plain HTTP in a way MCEN can see.
2. MCEN may still be classifying the domain by reputation even after HTTPS is corrected.

## What The App Already Does

These items are already implemented in the application:

- Forces secure cookies in production
- Redirects `www.mclbpd.com` to `https://mclbpd.com`
- Redirects proxied HTTP requests to HTTPS when `X-Forwarded-Proto=http`
- Adds security headers:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: SAMEORIGIN`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy`
  - `Cross-Origin-Opener-Policy`
  - `Strict-Transport-Security` when the request is HTTPS
- Publishes a sitemap at `/sitemap.xml`

Relevant files:

- `app/__init__.py`
- `app/config.py`
- `sitemap.xml`

## What Must Be True At The Edge

The app cannot solve these by itself. Cloudflare, IIS, Caddy, or another fronting proxy must do them correctly.

### 1. HTTP Must Redirect Before MCEN Reaches The App

Requirement:

- `http://mclbpd.com/*` must return a `301` or `308` to `https://mclbpd.com/*`

Preferred place to enforce it:

- Cloudflare: `SSL/TLS -> Edge Certificates -> Always Use HTTPS`
- Or a dedicated redirect rule at the edge

Notes:

- The Flask app only redirects when the proxy explicitly says the original request was HTTP.
- If the proxy never sends that signal, the app cannot detect the original scheme reliably.

### 2. TLS Must Terminate Correctly

Requirement:

- `https://mclbpd.com` must present a valid certificate
- No certificate warnings
- No mixed-content errors
- TLS 1.2 or higher

Recommended:

- Cloudflare SSL mode `Full` or `Full (strict)` if the origin certificate setup supports it

### 3. The Proxy Must Forward Original Scheme And Host

Requirement:

- Forward `X-Forwarded-Proto: https`
- Forward the public host name

This repo already assumes that behavior.

Examples already in the repo:

- `deploy/web.config.example`
- `deploy/Caddyfile.example`

### 4. The Origin Should Not Be Publicly Exposed

Preferred posture:

- Public traffic reaches Cloudflare or your reverse proxy
- The Flask dev server stays bound to localhost only

This reduces the chance that scanners see a bare self-hosted app server.

## Cloudflare Minimum Configuration

If Cloudflare is in front of the site, verify all of the following:

- Proxy status is enabled for the public hostname
- `Always Use HTTPS` is enabled
- `Automatic HTTPS Rewrites` is enabled
- Minimum TLS version is `1.2`
- SSL mode is `Full` or `Full (strict)`
- The public hostname points to the intended service or tunnel

If using Cloudflare Tunnel:

- Use a named tunnel, not a quick tunnel, for production
- Point the public hostname to `http://127.0.0.1:5055`
- Keep the tunnel service running continuously

Reference:

- `deploy/CLOUDFLARE_ACCESS_SETUP.md`

## Optional Hardening At The Edge

These may help consistency, but they are not substitutes for correct HTTPS and reputation handling:

- Add HSTS at the edge if you want the browser to receive it even before the request reaches Flask
- Enable Cloudflare bot protection
- Add a canonical redirect from `www.mclbpd.com` to `mclbpd.com`

Do not rely on edge-only headers as proof the site will be reclassified by MCEN.

## Reputation And Categorization

Even after HTTPS is fixed, MCEN may keep the domain blocked until its categorization updates.

Useful supporting signals:

- Stable HTTPS availability
- No downtime during scans
- Valid sitemap
- Search indexing
- No malware or browser safety flags
- Consistent DNS and hosting behavior

Important:

- Moving the site behind Cloudflare can improve how the origin is perceived.
- It does not guarantee MCEN access by itself.
- A waiver or recategorization request may still be required if the domain remains flagged.

## Verification Steps

From any non-MCEN network, verify:

1. `http://mclbpd.com` immediately redirects to `https://mclbpd.com`
2. `https://mclbpd.com` loads without certificate warnings
3. Response headers include the expected security headers
4. `https://mclbpd.com/sitemap.xml` loads
5. The site remains reachable over time and does not intermittently fail

If those checks pass and MCEN still blocks the site as `Suspicious`, the remaining problem is likely categorization rather than missing Flask code.
