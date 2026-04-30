# IIS Manager Checklist

This is the practical IIS Manager workflow for putting the Flask app behind IIS with certificate-based access.

## Before You Start

- Flask app running locally on `http://127.0.0.1:5055`
- IIS installed
- URL Rewrite installed
- Application Request Routing (ARR) installed
- Client Certificate Mapping Authentication installed
- HTTPS binding and server certificate ready for the IIS site

## 1. Enable ARR Proxy

1. Open IIS Manager.
2. Click the server node in the left tree.
3. Open `Application Request Routing Cache`.
4. In the right pane, click `Server Proxy Settings...`.
5. Check `Enable proxy`.
6. Click `Apply`.

This is required before IIS will forward requests to the Flask app.

## 2. Configure the Site Binding

1. Select the site that will front the portal.
2. In the right pane, click `Bindings...`.
3. Add or edit an `https` binding for your public hostname.
4. Select the server certificate for that hostname.
5. Save the binding.

## 3. Require SSL and Client Certificates

1. Select the site.
2. Open `SSL Settings`.
3. Check `Require SSL`.
4. Under `Client certificates`, choose:
   - `Require` if every visitor must present a valid certificate before reaching the site.
   - `Accept` if you want the site to load and only enforce identity when using the `CAC Login` button.
5. Click `Apply`.

If you want strict CAC-only access, use `Require`.

## 4. Enable IIS Client Certificate Mapping

1. Select the site.
2. Open `Authentication`.
3. Enable `IIS Client Certificate Mapping Authentication`.
4. Disable `Anonymous Authentication` if you want the entire site protected by certificate auth.

This causes IIS to authenticate the client cert to an IIS identity that can be exposed as `LOGON_USER`.

## 5. Add Certificate Mappings

For one-to-one mappings:

1. Select the site.
2. Open `Configuration Editor`.
3. In `Section`, choose `system.webServer/security/authentication/iisClientCertificateMappingAuthentication`.
4. Set `enabled` to `True`.
5. Set `oneToOneCertificateMappingsEnabled` to `True`.
6. Open `oneToOneMappings`.
7. Add a mapping:
   - `certificate`: base64 certificate blob
   - `userName`: Windows account to map to
   - `password`: password for that account
   - `enabled`: `True`
8. Click `Apply`.

Use one-to-one mappings if you need exact certificate-to-account control.

## 6. Add the Reverse Proxy Rule

1. Select the site.
2. Open `URL Rewrite`.
3. Choose `Add Rule(s)...`.
4. Pick `Reverse Proxy`.
5. Enter `127.0.0.1:5055` as the backend server.
6. Confirm the prompt to enable proxy if IIS asks again.

After the rule is created, make sure the site is using the settings shown in [web.config.example](/C:/Users/rober/Desktop/mcpd-portal/deploy/web.config.example).

## 7. Forward the Authenticated Identity Header

1. Open the site's `web.config` or use Configuration Editor.
2. Ensure IIS is allowed to set:
   - `HTTP_X_AUTHENTICATED_USER`
   - `HTTP_X_AUTHENTICATED_NAME`
3. Set both values to `{LOGON_USER}` before the rewrite action.

That is what the Flask app reads as `X-Authenticated-User` and `X-Authenticated-Name`.

## 8. Set App Environment

In `.env`, use:

```env
APP_ENV=prod
APP_DOMAIN=mclbpd.com
PREFERRED_URL_SCHEME=https
SESSION_COOKIE_SECURE=1
CAC_AUTH_ENABLED=1
CAC_AUTO_REGISTER=1
CAC_DEBUG_ENABLED=0
CAC_USERNAME_HEADER=X-Authenticated-User
CAC_NAME_HEADER=X-Authenticated-Name
```

## 9. Validate

1. Restart IIS.
2. Load the public HTTPS URL.
3. Complete the certificate prompt.
4. Click `CAC Login`.
5. If needed, temporarily enable `CAC_DEBUG_ENABLED=1` and use `Check CAC Headers` to confirm what reached Flask.

## Common Failure Points

- ARR proxy not enabled
- URL Rewrite not installed
- SSL Settings left on `Ignore`
- Client certificate mapping enabled but no mappings configured
- IIS forwarding raw certificate material instead of a mapped identity
- `LOGON_USER` empty because the cert was not actually authenticated
