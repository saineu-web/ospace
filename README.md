# Ospace — website + driver onboarding portal

Rebuild of [ospacegroup.com](https://www.ospacegroup.com) (student transportation, Houston TX) as one
Django app:

- **Marketing site** at `/` — every page and fact from the old Wix site, reorganised, plus new tools
  (earnings calculator, requirements self-check, quick-apply, ride-request and contact forms, FAQ,
  SEO/sitemap/JSON-LD, old Wix URLs redirected).
- **Driver onboarding flow** — the website apply form creates a driver profile with status
  **Interested** (no password yet) and emails `ONBOARDING_INBOX`. Staff **Activate** it from the
  staff desk (status → **In progress**; the driver gets a personal 7-day link to set a password and
  upload documents) or **Delete** it permanently. Then: profile → uploads → e-signed agreements
  (drawn signature + typed name, PDF copy with SHA-256 hash) → submit → Approved / Not approved.
  Self-registration is closed; `/portal/register/` redirects to the apply form.
- **Staff desk** at `/staff/` — activate/delete applicants, review documents, approve/reject drivers,
  message them. Full Django admin at `/admin/` for document requirements, agreement templates and
  website inquiries (ride requests, contact messages).

## Run locally

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_portal          # default document types + agreement templates (idempotent)
python manage.py createsuperuser
python manage.py runserver 8060
```

Mail prints to the console until `EMAIL_HOST` is set (see `.env.example`).

## Editing the documents drivers must upload / sign

Nothing is hard-coded. In `/admin/`:

- **Driver portal › Document types** — name, instructions, required?, ask for expiry date?, order.
- **Driver portal › Agreement templates** — plain-text body, blank line between paragraphs, `# ` starts
  a heading. Placeholders: `{{driver_name}} {{driver_email}} {{driver_phone}} {{date}} {{company}}
  {{vehicle}}`. **Bump `version` after changing wording** — drivers who signed the old text are asked
  to sign again; their old signed copy is kept.

The generic defaults live in `apps/portal/management/commands/seed_portal.py`.

## Languages (English, Spanish, Arabic)

English is served at `/`, Spanish at `/es/...`, Arabic at `/ar/...` (right-to-left). The header
and footer carry a switcher and every page emits `hreflang` links. Translations live in
`locale/es.json` and `locale/ar.json` (English string -> translation). After editing either file,
or after adding `{% translate %}` strings to a template, run:

```bash
python scripts/i18n_build.py
```

It regenerates the `.po`/`.mo` files (no GNU gettext needed) and prints any string that still
lacks a translation. The privacy policy and the signed agreements stay in English on purpose.

## Where things live

| Path | What |
|---|---|
| `config/settings.py` | `SITE` dict = phone, email, socials, app-store links, service number |
| `apps/web/` | marketing pages, forms → `Inquiry` model + email to `CONTACT_INBOX` |
| `apps/web/privacy_policy.txt` | the original privacy policy text, verbatim |
| `apps/portal/` | driver models, portal views, staff views, PDF builder, mail |
| `private/` | driver uploads + signatures + signed PDFs — **never served statically**, only via permission-checked views |
| `static/img/` | logo (transparent + white), favicon, photos from the old site |

## Deploy (VPS, same pattern as rodsign / huntcustomer)

**Live at https://www.ospacegroup.com since 2026-10-07.** DNS stays at Wix's nameservers
(A `@` and CNAME `www` point at the VPS; Google Workspace mail records untouched). Caddy holds
the Let's Encrypt certificates and 308s the bare domain to www. The site also reports traffic
and sign-ups to Zet8 Pulse (`PULSE_TOKEN` in the server `.env`).

`deploy.sh` ships the repo to the BioFleet VPS and restarts a gunicorn systemd unit behind Caddy.
One-time server setup is documented inside the script. Alternatively the `Procfile` works on
Railway/Render with `DATABASE_URL` + a persistent volume mounted at `PRIVATE_ROOT`.

Required env in production: `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`, `SITE_URL`, `EMAIL_*`,
`CONTACT_INBOX`, `ONBOARDING_INBOX` (default onboarding@ospacegroup.com), `SQLITE_PATH` (outside the app dir), and `PRIVATE_ROOT`/`MEDIA_ROOT` on
persistent disk.

## Still outstanding (needs Ospace's input)

- Real document list + real agreement wording (replace the generic seed in `/admin/`).
- LinkedIn URL (`SITE["linkedin"]`) — the old site linked to Wix's own LinkedIn page.
- Confirm pricing copy ("$25 drop-off", "$50 per 2 rides", "$150+/day") — all taken from the old site.
- Privacy policy names "Ospace Advanced Technologies, Inc." and "www.ospace.com" — copied as-is from the old site; legal should review.
- SMTP credentials so form submissions and portal emails actually send.
