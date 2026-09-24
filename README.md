# Ospace — website + driver onboarding portal

Rebuild of [ospacegroup.com](https://www.ospacegroup.com) (student transportation, Houston TX) as one
Django app:

- **Marketing site** at `/` — every page and fact from the old Wix site, reorganised, plus new tools
  (earnings calculator, requirements self-check, quick-apply, ride-request and contact forms, FAQ,
  SEO/sitemap/JSON-LD, old Wix URLs redirected).
- **Driver portal** at `/portal/` — drivers register, complete a profile, upload documents, e-sign
  agreements (drawn signature + typed name, PDF copy with SHA-256 hash), and submit for review.
- **Staff desk** at `/staff/` — review documents, approve/reject drivers, message them. Full Django
  admin at `/admin/` for editing document requirements, agreement templates and website inquiries.

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

`deploy.sh` rsyncs the repo to the BioFleet VPS and restarts a gunicorn systemd unit behind Caddy.
One-time server setup is documented inside the script. Alternatively the `Procfile` works on
Railway/Render with `DATABASE_URL` + a persistent volume mounted at `PRIVATE_ROOT`.

Required env in production: `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`, `SITE_URL`, `EMAIL_*`,
`CONTACT_INBOX`, and `PRIVATE_ROOT`/`MEDIA_ROOT` on persistent disk.

## Before go-live (needs Ospace's input)

- Real document list + real agreement wording (replace the generic seed in `/admin/`).
- LinkedIn URL (`SITE["linkedin"]`) — the old site linked to Wix's own LinkedIn page.
- Confirm pricing copy ("$25 drop-off", "$50 per 2 rides", "$150+/day") — all taken from the old site.
- Privacy policy names "Ospace Advanced Technologies, Inc." and "www.ospace.com" — copied as-is from the old site; legal should review.
- SMTP credentials so form submissions and portal emails actually send.
