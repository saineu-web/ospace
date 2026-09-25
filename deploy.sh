#!/usr/bin/env bash
#
# Ospace deploy — rsync the repo to the VPS, install deps, migrate, collectstatic, restart gunicorn.
# Run from the repo root in Git Bash:   ./deploy.sh
#
# ONE-TIME SERVER SETUP (root@VPS):
#   adduser --system --group --home /srv/ospace ospace
#   mkdir -p /srv/ospace/{app,private,media} && chown -R ospace:ospace /srv/ospace
#   apt install -y python3-venv && sudo -u ospace python3 -m venv /srv/ospace/venv
#   cat > /srv/ospace/app/.env   (copy .env.example, DEBUG=0, real SECRET_KEY, PRIVATE_ROOT=/srv/ospace/private, MEDIA_ROOT=/srv/ospace/media)
#   cat > /etc/systemd/system/ospace.service <<'UNIT'
#   [Unit]
#   Description=Ospace (gunicorn)
#   After=network.target
#   [Service]
#   User=ospace
#   WorkingDirectory=/srv/ospace/app
#   EnvironmentFile=/srv/ospace/app/.env
#   ExecStart=/srv/ospace/venv/bin/gunicorn config.wsgi --bind 127.0.0.1:8060 --workers 3 --timeout 60
#   Restart=always
#   [Install]
#   WantedBy=multi-user.target
#   UNIT
#   systemctl enable --now ospace
#   Caddyfile block:
#     ospacegroup.com, www.ospacegroup.com {
#       redir https://www.ospacegroup.com{uri} 308   # only in the apex block
#       reverse_proxy 127.0.0.1:8060
#       request_body { max_size 12MB }
#     }
set -euo pipefail

HOST="${OSPACE_HOST:-root@46.62.146.65}"
KEY="${OSPACE_KEY:-$HOME/.ssh/huntcustomer_deploy}"
DEST="/srv/ospace/app"

echo "== Uploading to $HOST:$DEST =="
# Git Bash on Windows has no rsync, so ship a tarball and let the server rsync it into place
# (server-side --delete keeps the app dir an exact mirror, while .env survives untouched).
tar -czf -   --exclude=".git" --exclude="venv" --exclude="__pycache__" --exclude="*.pyc"   --exclude="db.sqlite3" --exclude="media" --exclude="private" --exclude="staticfiles"   --exclude=".env" --exclude="source-media" --exclude=".claude"   . | ssh -i "$KEY" "$HOST" "rm -rf /srv/ospace/incoming && mkdir -p /srv/ospace/incoming && tar -xzf - -C /srv/ospace/incoming   && rsync -a --delete --exclude .env --exclude db.sqlite3 /srv/ospace/incoming/ $DEST/ && rm -rf /srv/ospace/incoming"

ssh -o BatchMode=yes -i "$KEY" "$HOST" "
  set -e
  cd $DEST
  chown -R ospace:ospace /srv/ospace
  sudo -u ospace /srv/ospace/venv/bin/pip install -q -r requirements.txt
  sudo -u ospace /srv/ospace/venv/bin/python manage.py migrate --noinput
  sudo -u ospace /srv/ospace/venv/bin/python manage.py seed_portal
  sudo -u ospace /srv/ospace/venv/bin/python manage.py collectstatic --noinput
  systemctl restart ospace
  sleep 2
  systemctl is-active ospace
  curl -sf http://127.0.0.1:8060/healthz
" && echo "" && echo "== deploy OK =="
