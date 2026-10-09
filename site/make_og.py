"""Render the 1200×630 link-preview card for each locale into assets/og-<locale>.png.

Uses the locale's Home eyebrow and heading so a shared link previews in the reader's language.
Rerun after changing the Home heading or the app icon; build.py then copies the cards like any asset.
"""
from html import escape
from pathlib import Path
import json, subprocess, tempfile

ROOT = Path(__file__).resolve().parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
ICON = ROOT / 'assets' / 'apple-touch-icon.png'
CARD = '''<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
body{{background:#f7f0df;color:#34252d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
display:flex;align-items:center;gap:72px;padding:0 96px;box-sizing:border-box}}
img{{width:260px;height:260px;border-radius:58px;box-shadow:0 18px 40px #34252d26;flex-shrink:0}}
.brand{{font:52px Georgia,serif;letter-spacing:-.03em;margin-bottom:26px}}.brand span{{color:#875119}}
h1{{font:400 {size}px/1.1 Georgia,"Times New Roman",serif;letter-spacing:-.03em;margin:0 0 30px}}
.eyebrow{{font:650 21px/1.5 ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:#875119}}
{cjk}</style><img src="{icon}"><div><div class="brand"><span>e</span>verglow</div><h1>{l1}<br><em>{l2}</em></h1><div class="eyebrow">{eyebrow}</div></div>'''

source = json.loads((ROOT / 'locales/source.json').read_text())
with tempfile.TemporaryDirectory() as tmp:
    for locale in ('en', 'zh', 'ja', 'fr', 'es'):
        home = (source if locale == 'en' else json.loads((ROOT / 'locales' / (locale + '.json')).read_text()))['pages']['home']
        page = Path(tmp) / (locale + '.html')
        # Long Latin headings shrink so each authored line stays one line; CJK has no true italic, so no faux slant.
        em = lambda t: sum(1.0 if ord(c) >= 0x2E80 else 0.45 for c in t)  # CJK glyphs are full-width
        size = min(62, int(670 / max(em(home[1]), em(home[2]))))
        cjk = 'em{font-style:normal}' if locale in ('zh', 'ja') else ''
        page.write_text(CARD.format(size=size, cjk=cjk, icon=ICON.as_uri(), eyebrow=escape(home[0]), l1=escape(home[1]), l2=escape(home[2])))
        out = ROOT / 'assets' / ('og-' + locale + '.png')
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                        '--window-size=1200,630', '--screenshot=' + str(out), page.as_uri()], check=True, capture_output=True, timeout=60)
        print(out.name, out.stat().st_size)
