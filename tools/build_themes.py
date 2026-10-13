"""Build the themed versions of the Waffle Amour site.

Copies index.html and recipes.html from waffle-amour-site/ into
  waffle-amour-site/dark/   (opens in Dark Chocolate mode)
  waffle-amour-site/light/  (opens in All-Light mode)
Both copies load both theme stylesheets and carry a light/dark toggle in the
header (and the footer link), which switches instantly and remembers the
visitor's choice. The folder only sets the default for first-time visitors.
Re-run after editing the base pages:

    python tools/build_themes.py
"""
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent   # the website folder (this script lives in tools/)
COPYRIGHT = '<span>© <span id="yr"></span> Waffle Amour™. All rights reserved.</span>'
CSS = {"dark": "../dark/theme-choc.css", "light": "../light/theme-light.css"}

HEAD = """<link id="css-dark" rel="stylesheet" href="{dark}" media="{dark_media}">
<link id="css-light" rel="stylesheet" href="{light}" media="{light_media}">
<script>
/* Theme: this folder's default unless the visitor picked one before. Runs before paint. */
(function(){{var t='{default}',s;try{{s=localStorage.getItem('wa-theme')}}catch(e){{}}
if(s==='dark'||s==='light')t=s;document.documentElement.dataset.theme=t;
document.getElementById('css-dark').media=t==='dark'?'all':'not all';
document.getElementById('css-light').media=t==='light'?'all':'not all';}})();
</script>
<style>
.theme-toggle{{position:relative;flex:none;width:58px;height:30px;padding:0;border-radius:999px;cursor:pointer;color:inherit;
  border:1.5px solid rgba(201,162,74,.65);background:rgba(127,110,90,.14);transition:border-color .2s}}
.theme-toggle:hover{{border-color:#c9a24a}}
.theme-toggle::after{{content:"";position:absolute;inset:-8px -4px}}
.theme-toggle:focus-visible{{outline:2px solid #c9a24a;outline-offset:3px}}
.theme-toggle svg{{position:absolute;top:50%;width:14px;height:14px;transform:translateY(-50%);opacity:.7}}
.theme-toggle .i-sun{{left:7px}}.theme-toggle .i-moon{{right:7px}}
.theme-toggle .knob{{position:absolute;top:2px;left:2px;width:23px;height:23px;border-radius:50%;z-index:1;
  background:linear-gradient(135deg,#f3dfa2,#c9a24a 55%,#9a7426);box-shadow:0 2px 6px rgba(0,0,0,.3);transition:transform .35s cubic-bezier(.2,.8,.2,1)}}
[data-theme="dark"] .theme-toggle .knob{{transform:translateX(28px)}}
.nav .theme-toggle{{margin-left:auto;margin-right:-6px}}
@media (prefers-reduced-motion:reduce){{.theme-toggle .knob{{transition:none}}}}
</style>
"""

BODY = """<script>
/* Light/dark toggle: swaps theme stylesheet + logo instantly and remembers the choice */
(function(){
  const root = document.documentElement;
  const css = { dark: document.getElementById('css-dark'), light: document.getElementById('css-light') };
  const LOGO = { dark: '../images/logo-white.png', light: '../images/logo.png' };
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'theme-toggle';
  btn.innerHTML = '<span class="knob"></span>'
    + '<svg class="i-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
    + '<svg class="i-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  const nav = document.querySelector('.nav');
  nav.insertBefore(btn, nav.querySelector('.btn') || nav.querySelector('.menu-btn'));
  const sw = document.querySelector('.theme-switch');

  function paint(t){
    css.dark.media = t === 'dark' ? 'all' : 'not all';
    css.light.media = t === 'light' ? 'all' : 'not all';
    root.dataset.theme = t;
    document.querySelectorAll('.logo-img, .pl-logo').forEach(i => { i.src = LOGO[t]; });
    btn.setAttribute('aria-pressed', String(t === 'dark'));
    btn.setAttribute('aria-label', t === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    btn.title = btn.getAttribute('aria-label');
    if (sw) sw.textContent = t === 'dark' ? 'View light version' : 'View dark version';
  }
  function toggle(e){
    if (e) e.preventDefault();
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('wa-theme', next); } catch(err) {}
    if (document.startViewTransition && !matchMedia('(prefers-reduced-motion: reduce)').matches) document.startViewTransition(() => paint(next));
    else paint(next);
  }
  btn.addEventListener('click', toggle);
  if (sw) sw.addEventListener('click', toggle);
  paint(root.dataset.theme);
})();
</script>
"""

VARIANTS = {"dark": "light", "light": "dark"}   # folder -> the other mode (footer link fallback target)

for folder, other in VARIANTS.items():
    out = SITE / folder
    for name in ["index.html", "recipes.html"]:
        html = (SITE / name).read_text(encoding="utf-8")
        html = re.sub(r'(?<![\w./])(images|videos)/', r'../\1/', html)
        if folder == "light":
            html = html.replace("../images/logo-white.png", "../images/logo.png")
        head = HEAD.format(dark=CSS["dark"], light=CSS["light"], default=folder,
                           dark_media="all" if folder == "dark" else "not all",
                           light_media="all" if folder == "light" else "not all")
        html = html.replace("</head>", head + "</head>", 1)
        assert COPYRIGHT in html, f"footer copyright line not found in {name}"
        html = html.replace(
            COPYRIGHT,
            COPYRIGHT[:-7] + f' · <a class="theme-switch" href="../{other}/{name}">View {other} version</a></span>', 1)
        html = html.replace("</body>", BODY + "</body>", 1)
        (out / name).write_text(html, encoding="utf-8")
        print(f"built {folder}/{name}")
