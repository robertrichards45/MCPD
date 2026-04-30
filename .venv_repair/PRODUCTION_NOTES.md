# Production Notes

## Security
- Set a strong `SECRET_KEY`
- Use HTTPS only
- Configure secure cookies (SESSION_COOKIE_SECURE)
- Restrict upload file types or scan uploads
- Use a WAF or reverse proxy (Nginx/IIS)

## Hardening
- Disable debug mode in production
- Rotate admin password and limit admin accounts
- Enable audit log review

## Backups
- Backup `data/app.db` and `data/uploads` daily

## Scaling
- Move SQLite to Postgres if concurrent load increases
- Move uploads to shared storage

## Deployment Guides
- MCEN edge and categorization checklist: `deploy\MCEN_EDGE_CHECKLIST.md`
- Cloudflare checklist for `mclbpd.com`: `deploy\CLOUDFLARE_MCLBPD_CHECKLIST.md`
- IIS CAC overview: `deploy\IIS_CAC_SETUP.md`
- IIS click-by-click checklist: `deploy\IIS_MANAGER_CHECKLIST.md`
- IIS sample proxy config: `deploy\web.config.example`
- Caddy CAC setup: `deploy\CADDY_CAC_SETUP.md`
- Caddy sample config: `deploy\Caddyfile.example`
- Temporary Cloudflare Access external login: `deploy\CLOUDFLARE_ACCESS_SETUP.md`

