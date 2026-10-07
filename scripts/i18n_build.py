#!/usr/bin/env python
"""Build the Spanish and Arabic translations without GNU gettext.

Neither the Windows dev box nor the VPS has xgettext/msgfmt, so this script does what
`makemessages` + `compilemessages` would do:

  1. Extract every translatable string from templates ({% translate %}, {% blocktranslate %})
     and Python code (_(), gettext(), gettext_lazy(), pgettext*).
  2. Merge them with the human-written translations in locale/<lang>.json
     (msgid -> msgstr; edit these files to change wording).
  3. Write locale/<lang>/LC_MESSAGES/django.po and compile django.mo with polib.

Run:  python scripts/i18n_build.py          (prints any string that still lacks a translation)
      python scripts/i18n_build.py --check  (exit 1 if anything is untranslated)
"""
import json
import re
import sys
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent
LANGS = ["es", "ar"]

TEMPLATE_DIRS = [ROOT / "templates"]
PY_DIRS = [ROOT / "apps"]

RE_TRANS = re.compile(r"""{%\s*trans(?:late)?\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""")
RE_BLOCK = re.compile(r"{%\s*blocktrans(?:late)?(?P<args>[^%]*)%}(?P<body>.*?){%\s*endblocktrans(?:late)?\s*%}", re.S)
RE_PY = re.compile(r"""(?<![\w.])(?:_|gettext|gettext_lazy|ngettext|pgettext|pgettext_lazy)\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""")


def _unescape(s):
    return s.replace('\\"', '"').replace("\\'", "'")


def extract():
    ids = {}

    def add(msgid, where):
        if msgid and msgid not in ids:
            ids[msgid] = where

    for d in TEMPLATE_DIRS:
        for f in d.rglob("*.html"):
            text = f.read_text(encoding="utf-8")
            rel = str(f.relative_to(ROOT))
            for m in RE_TRANS.finditer(text):
                add(_unescape(m.group(1) or m.group(2) or ""), rel)
            for m in RE_BLOCK.finditer(text):
                body = m.group("body")
                if "trimmed" in m.group("args"):
                    body = " ".join(line.strip() for line in body.strip().splitlines())
                add(body, rel)
    for d in PY_DIRS:
        for f in d.rglob("*.py"):
            if "migrations" in f.parts:
                continue
            text = f.read_text(encoding="utf-8")
            rel = str(f.relative_to(ROOT))
            for m in RE_PY.finditer(text):
                add(_unescape(m.group(1) or m.group(2) or ""), rel)
    return ids


def build(check=False):
    ids = extract()
    missing_total = 0
    for lang in LANGS:
        src = ROOT / "locale" / f"{lang}.json"
        translations = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
        po = polib.POFile()
        po.metadata = {
            "Project-Id-Version": "ospace",
            "Language": lang,
            "MIME-Version": "1.0",
            "Content-Type": "text/plain; charset=UTF-8",
            "Content-Transfer-Encoding": "8bit",
            "Plural-Forms": "nplurals=2; plural=(n != 1);" if lang == "es" else "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);",
        }
        missing = []
        for msgid, where in ids.items():
            msgstr = translations.get(msgid, "")
            if not msgstr:
                missing.append(msgid)
            po.append(polib.POEntry(msgid=msgid, msgstr=msgstr, occurrences=[(where, "")]))
        out = ROOT / "locale" / lang / "LC_MESSAGES"
        out.mkdir(parents=True, exist_ok=True)
        po.save(str(out / "django.po"))
        po.save_as_mofile(str(out / "django.mo"))
        stale = [k for k in translations if k not in ids]
        print(f"[{lang}] {len(ids)} strings, {len(ids) - len(missing)} translated, {len(missing)} missing, {len(stale)} stale")
        for m in missing:
            print(f"   MISSING: {m[:110]!r}")
        for m in stale[:10]:
            print(f"   stale (in json, not in code): {m[:90]!r}")
        missing_total += len(missing)
    if check and missing_total:
        sys.exit(1)


if __name__ == "__main__":
    build(check="--check" in sys.argv)
