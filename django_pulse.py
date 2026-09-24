"""Zet8 Pulse — drop-in traffic + signup reporting for a Django app.

One file. No new INSTALLED_APPS entry, no migration. Copy it next to the project's
settings module and wire it up with two lines (see INTEGRATION below).

WHY NO MIGRATION: this has to land in six separate Django repos, each with its own
migration history and its own deploy story. A model would mean six `makemigrations`
runs and six chances for a merge conflict in a numbered migration file. The two
tables here are pure counters with no relations and no FKs, so the ORM buys nothing;
they are created lazily with `CREATE TABLE IF NOT EXISTS`, which is identical SQL on
Postgres and SQLite. Integration cost is a settings edit and a url include.

WHAT IT COLLECTS: a per-day pageview count, and a per-day count of distinct visitors
where a "visitor" is sha256(SECRET_KEY | ip | user-agent | day) truncated to 20 hex
chars. That hash is not reversible to an IP, it is re-salted every day so the same
person is not linkable across days, and no cookie is set. That is deliberate — it
keeps this outside the scope of consent banners, and it means the counter table can
never become a liability if the box is compromised.

INTEGRATION (per app):

    # settings.py
    MIDDLEWARE = [
        "django_pulse.PulseMiddleware",   # near the top, above CommonMiddleware
        ...
    ]
    PULSE_APP = "onsms"                       # short slug, must match the collector registry
    PULSE_TOKEN = os.environ["PULSE_TOKEN"]   # shared secret for the read endpoint
    PULSE_SIGNUPS = [        # (label, "app_label.Model", "date field"[, extra filters])
        ("workers",   "accounts.User", "date_joined", {"role__in": ["worker", "both"]}),
        ("employers", "accounts.User", "date_joined", {"role__in": ["employer", "both"]}),
    ]

    # urls.py
    urlpatterns += [path("internal/pulse/", __import__("django_pulse").pulse_view)]

The endpoint is GET /internal/pulse/?token=...  and returns JSON. It is read-only and
returns counts only — never a row, an email, or an id.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import re

from django.apps import apps as _django_apps
from django.conf import settings
from django.db import connection
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse

# ---------------------------------------------------------------------------
# storage
# ---------------------------------------------------------------------------
# `day` is TEXT in ISO form rather than a DATE column: SQLite has no real date type,
# and keeping it TEXT everywhere means the same SQL string works on both backends
# without a per-backend cast. Ordering and BETWEEN still behave, since ISO dates sort
# lexicographically.
_DDL = (
    """CREATE TABLE IF NOT EXISTS pulse_daily (
           day   varchar(10) NOT NULL,
           kind  varchar(16) NOT NULL,
           n     integer     NOT NULL DEFAULT 0,
           PRIMARY KEY (day, kind)
       )""",
    """CREATE TABLE IF NOT EXISTS pulse_seen (
           day varchar(10) NOT NULL,
           vid varchar(20) NOT NULL,
           PRIMARY KEY (day, vid)
       )""",
)

_ready = False


def _ensure_tables(cur):
    global _ready
    if _ready:
        return
    for stmt in _DDL:
        cur.execute(stmt)
    _ready = True


# ---------------------------------------------------------------------------
# request filtering
# ---------------------------------------------------------------------------
_BOT = re.compile(
    r"bot|crawl|spider|slurp|bingpreview|facebookexternalhit|embedly|quora link|"
    r"pingdom|uptime|monitor|curl|wget|python-requests|okhttp|headless|lighthouse|"
    r"ahrefs|semrush|mj12|dotbot|petalbot|gptbot|claudebot|ccbot|bytespider",
    re.I,
)

# Paths that are machinery rather than someone looking at a page. Health checks in
# particular would otherwise dominate the numbers — Railway hits /healthz constantly,
# which would render the pageview column meaningless.
_SKIP_PREFIXES = (
    "/static/", "/media/", "/admin/", "/internal/", "/healthz", "/readyz",
    "/favicon", "/robots.txt", "/sitemap.xml", "/.well-known/",
)


def _client_ip(request) -> str:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        # Railway and Caddy both append; the original client is the first entry.
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _visitor_id(request, day: str) -> str:
    raw = "|".join((
        getattr(settings, "SECRET_KEY", ""),
        _client_ip(request),
        request.META.get("HTTP_USER_AGENT", "")[:200],
        day,  # re-salting per day makes the hash non-linkable across days
    ))
    return hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:20]


class PulseMiddleware:
    """Counts HTML pageviews and distinct daily visitors.

    Every failure path is swallowed. Analytics must never be the reason a page 500s,
    so a broken counter degrades to "no data for today" rather than an error.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.count_json = bool(getattr(settings, "PULSE_COUNT_JSON", False))

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if self._countable(request, response):
                self._record(request)
        except Exception:  # noqa: BLE001 - see class docstring
            pass
        return response

    def _countable(self, request, response) -> bool:
        if request.method != "GET":
            return False
        # 2xx only. A 3xx is not a page someone looked at, and counting it would
        # double-bill every login bounce: once for the redirect, once for the page.
        if not (200 <= response.status_code < 300):
            return False
        path = request.path or "/"
        if path.startswith(_SKIP_PREFIXES):
            return False
        ctype = (response.get("Content-Type") or "").lower()
        if not (ctype.startswith("text/html") or (self.count_json and "json" in ctype)):
            return False
        return not _BOT.search(request.META.get("HTTP_USER_AGENT", ""))

    def _record(self, request):
        day = _dt.date.today().isoformat()
        vid = _visitor_id(request, day)
        with connection.cursor() as cur:
            _ensure_tables(cur)
            # Both backends speak this form of upsert (SQLite >= 3.24, all supported
            # Postgres). Django's SQLite backend rewrites %s placeholders, so one
            # string serves both.
            cur.execute(
                "INSERT INTO pulse_daily (day, kind, n) VALUES (%s, 'view', 1) "
                "ON CONFLICT (day, kind) DO UPDATE SET n = pulse_daily.n + 1",
                [day],
            )
            cur.execute(
                "INSERT INTO pulse_seen (day, vid) VALUES (%s, %s) "
                "ON CONFLICT (day, vid) DO NOTHING",
                [day, vid],
            )


# ---------------------------------------------------------------------------
# read endpoint
# ---------------------------------------------------------------------------
def _series_from_model(spec: str, field: str, since: _dt.date, extra: dict | None = None) -> dict:
    """Count rows per day for one configured signup source.

    Grouped in the database via TruncDate, which Django renders correctly for both
    Postgres and SQLite, so no rows cross the wire. An earlier version streamed
    timestamps with .iterator(); that opens a server-side cursor, and on Postgres the
    cursor was invalidated by the autocommit between this and the traffic query
    ("InvalidCursorName"). Aggregating server-side sidesteps that entirely and is
    faster besides.
    """
    model = _django_apps.get_model(spec)
    qs = model.objects.filter(**{f"{field}__date__gte": since})
    if extra:
        qs = qs.filter(**extra)
    rows = (
        qs.annotate(_pulse_day=TruncDate(field))
          .values("_pulse_day")
          .annotate(n=Count("pk"))
          .order_by()  # clear any Meta.ordering, which would otherwise join the GROUP BY
    )
    return {r["_pulse_day"].isoformat(): r["n"] for r in rows if r["_pulse_day"]}


def pulse_view(request):
    """GET /internal/pulse/?token=...&days=60 -> JSON rollup. Counts only."""
    expected = str(getattr(settings, "PULSE_TOKEN", "") or "")
    supplied = request.GET.get("token", "") or request.META.get("HTTP_X_PULSE_TOKEN", "")
    # Constant-time compare so the endpoint can't be probed a character at a time.
    if not expected or not hmac.compare_digest(supplied, expected):
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        days = max(1, min(365, int(request.GET.get("days", 60))))
    except (TypeError, ValueError):
        days = 60
    since = _dt.date.today() - _dt.timedelta(days=days - 1)

    views: dict[str, int] = {}
    visitors: dict[str, int] = {}
    try:
        with connection.cursor() as cur:
            _ensure_tables(cur)
            cur.execute(
                "SELECT day, n FROM pulse_daily WHERE kind = 'view' AND day >= %s",
                [since.isoformat()],
            )
            views = {row[0]: row[1] for row in cur.fetchall()}
            cur.execute(
                "SELECT day, COUNT(*) FROM pulse_seen WHERE day >= %s GROUP BY day",
                [since.isoformat()],
            )
            visitors = {row[0]: row[1] for row in cur.fetchall()}
            # Opportunistic retention. The visitor table is the only one that grows
            # per-person, and nothing needs it past the dashboard's longest window.
            cur.execute(
                "DELETE FROM pulse_seen WHERE day < %s",
                [(_dt.date.today() - _dt.timedelta(days=120)).isoformat()],
            )
    except Exception as exc:  # noqa: BLE001
        views, visitors = {}, {}
        errors = [f"traffic: {exc.__class__.__name__}"]
    else:
        errors = []

    signups: dict[str, dict] = {}
    totals: dict[str, int] = {}
    for entry in getattr(settings, "PULSE_SIGNUPS", []):
        # A source is (label, model, date field) or (label, model, date field, filters).
        label, spec, field = entry[0], entry[1], entry[2]
        extra = entry[3] if len(entry) > 3 else None
        try:
            signups[label] = _series_from_model(spec, field, since, extra)
            qs = _django_apps.get_model(spec).objects
            totals[label] = (qs.filter(**extra) if extra else qs).count()
        except Exception as exc:  # noqa: BLE001 - one bad source must not blank the rest
            signups[label] = {}
            totals[label] = -1
            errors.append(f"{label}: {exc.__class__.__name__}: {exc}")

    return JsonResponse({
        "app": getattr(settings, "PULSE_APP", "unknown"),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "days": days,
        "views": views,
        "visitors": visitors,
        "signups": signups,
        "totals": totals,
        "errors": errors,
    })
