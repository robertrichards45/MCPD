# MCPD Hybrid Auth Deployment Runbook

This is the production deployment checklist for the hybrid model:

- public username/password login remains available
- account creation requires CAC
- sensitive modules require CAC and a valid portal session
- Cloudflare DNS is used, but the site record should be `DNS only` for direct mTLS

## 1. Ubuntu VM

Provision an Ubuntu LTS VM and open:

- `22/tcp`
- `80/tcp`
- `443/tcp`

Install:

```bash
sudo apt update
sudo apt install -y nginx git ufw certbot python3-certbot-nginx python3 python3-venv python3-pip
```

Firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 2. DNS

Cloudflare:

- `A` record `mclbpd.com` -> VM public IP
- optional `www` -> redirect to apex or matching record
- keep the website hostname `DNS only` so client certificate auth reaches nginx

## 3. HTTPS

Issue Let’s Encrypt certs:

```bash
sudo certbot --nginx -d mclbpd.com
```

If `www` is used:

```bash
sudo certbot --nginx -d mclbpd.com -d www.mclbpd.com
```

## 4. DoD CA Bundle

Place the DoD PKI trust bundle at:

```bash
/etc/ssl/certs/dod_pki_ca_bundle.pem
```

## 5. Nginx Reverse Proxy + CAC

Use nginx to terminate TLS and proxy to the app on `127.0.0.1:8000`.

Global TLS:

- `ssl_verify_client optional;`
- `ssl_client_certificate /etc/ssl/certs/dod_pki_ca_bundle.pem;`

Routes that should require CAC:

- `/account/create`
- `/account/cac/`
- `/account/link-cac`
- `/armory/`
- `/truck-gate/`
- `/rfi/`

Before proxying, strip inbound spoofed CAC headers and set trusted ones:

- `X-CAC-VERIFY`
- `X-CAC-SUBJECT-DN`
- `X-CAC-ISSUER-DN`
- `X-CAC-SERIAL`
- `X-CAC-IDENTIFIER`

## 6. App Service

Run the app bound only to localhost:

```bash
127.0.0.1:8000
```

Environment should include:

- `APP_ENV=prod`
- `FORCE_HTTPS=1`
- `TRUST_PROXY=1`
- `CAC_AUTH_ENABLED=1`

## 7. GitHub Actions Auto-Deploy

Target layout:

- app path: `/opt/mclbpd/app`
- deploy script: `/opt/mclbpd/deploy.sh`
- service name: `mclbpd.service`

Workflow:

1. push to `main`
2. GitHub Actions SSHes to the VM
3. run `/opt/mclbpd/deploy.sh`
4. restart `mclbpd.service`

Secrets expected in GitHub:

- `PROD_HOST`
- `PROD_USER`
- `PROD_SSH_KEY`

## 8. Acceptance Checks

Public login:

- `https://mclbpd.com/login` works without CAC

CAC account creation:

- `https://mclbpd.com/account/create` requires CAC

Sensitive modules:

- `/armory`
- `/truck-gate`
- `/rfi`

Each should require:

1. valid session
2. correct role
3. verified CAC at nginx

## 9. Current App Routes Already Prepared

These app routes already exist in the codebase:

- `/admin/login`
- `/cac/login`
- `/account/cac/start`
- `/account/create`
- `/account/link-cac`
- `/healthz`
- `/status.json`
- `/version.json`

The app-side sensitive module guard is also already wired and activates when:

- `CAC_AUTH_ENABLED=1`

