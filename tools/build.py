"""Build the Waffle Amour website into public/.

Reads the page templates in src/ and the data in src/data/, and writes:
  public/index.html                      homepage (product range written into the page)
  public/recipes/index.html              recipe list
  public/recipes/<slug>/index.html       one page per recipe, with Recipe structured data
  public/404.html                        "page not found"
  public/css/                            the two theme stylesheets
  public/sitemap.xml + robots.txt        only once SITE_URL is set
Images, video and icons live in public/ already and are not touched.

Every page carries the light/dark toggle (default below; the visitor's choice is
remembered). Run after any edit in src/:

    python tools/build.py
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "src", ROOT / "public"

# Set once the domain is live, e.g. "https://www.waffleamour.co.uk". Adds canonical
# links, full share-image addresses, sitemap.xml and robots.txt.
SITE_URL = ""
DEFAULT_THEME = "dark"

COPYRIGHT = '<span>© <span id="yr"></span> Waffle Amour™. All rights reserved.</span>'
SHARE_IMAGE = "/images/share.jpg"

# ---------------------------------------------------------------------------- light/dark toggle
THEME_HEAD = """<link id="css-dark" rel="stylesheet" href="/css/theme-choc.css" media="{dark_media}">
<link id="css-light" rel="stylesheet" href="/css/theme-light.css" media="{light_media}">
<script>
/* Theme: the site default unless the visitor picked one before. Runs before paint. */
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

THEME_BODY = """<script>
/* Light/dark toggle: swaps theme stylesheet + logo instantly and remembers the choice */
(function(){
  const root = document.documentElement;
  const css = { dark: document.getElementById('css-dark'), light: document.getElementById('css-light') };
  const LOGO = { dark: '/images/logo-white.png', light: '/images/logo.png' };
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

# ---------------------------------------------------------------------------- small helpers
def esc(s):
    return html.escape(str(s), quote=True)

def abs_url(path):
    return SITE_URL.rstrip("/") + path if SITE_URL else path

def json_for_html(data):
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

ARROW = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
         '<path d="M5 12h14M13 5l7 7-7 7"/></svg>')
ICO_TIME = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
            '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>')
ICO_PRINT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">'
             '<path d="M6 9V3h12v6M6 18H4v-7h16v7h-2M7 14h10v7H7z"/></svg>')

def finish(page, *, path, title, desc, og_title=None, og_desc=None, og_image=SHARE_IMAGE, og_type="website", head_extra=""):
    """Fill head tokens, make every link/asset path work from any folder, add the toggle."""
    extra = []
    if SITE_URL:
        extra.append(f'<link rel="canonical" href="{esc(abs_url(path))}">')
        extra.append(f'<meta property="og:url" content="{esc(abs_url(path))}">')
    if head_extra:
        extra.append(head_extra)
    for token, value in {
        "@@TITLE@@": title, "@@DESC@@": desc, "@@OG_TYPE@@": og_type,
        "@@OG_TITLE@@": og_title or title, "@@OG_DESC@@": og_desc or desc, "@@OG_IMAGE@@": abs_url(og_image),
    }.items():
        page = page.replace(token, esc(value))
    page = page.replace("<!--@HEAD_EXTRA-->", "\n".join(extra))

    # Root-relative paths, so pages work at any depth (/recipes/<slug>/)
    page = re.sub(r'(?<![\w./])(images|videos)/', r'/\1/', page)
    for icon in ["favicon.ico", "favicon-32.png", "apple-touch-icon.png"]:
        page = page.replace(f'href="{icon}"', f'href="/{icon}"')
    page = re.sub(r'recipes\.html#([a-z0-9-]+)', r'/recipes/\1/', page)
    page = page.replace('href="recipes.html"', 'href="/recipes/"')
    page = page.replace('href="index.html#', 'href="/#').replace('href="index.html"', 'href="/"')

    # Light/dark toggle
    page = page.replace("</head>", THEME_HEAD.format(
        default=DEFAULT_THEME,
        dark_media="all" if DEFAULT_THEME == "dark" else "not all",
        light_media="all" if DEFAULT_THEME == "light" else "not all") + "</head>", 1)
    assert COPYRIGHT in page, "footer copyright line not found"
    other = "light" if DEFAULT_THEME == "dark" else "dark"
    page = page.replace(COPYRIGHT, COPYRIGHT[:-7] + f' · <a class="theme-switch" href="#">View {other} version</a></span>', 1)
    page = page.replace("</body>", THEME_BODY + "</body>", 1)
    assert "@@" not in page, f"unfilled token in {path}"
    return page

def write(rel, text):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    print("built", rel)

# ---------------------------------------------------------------------------- data
products = json.loads((SRC / "data" / "products.json").read_text(encoding="utf-8"))
rdata = json.loads((SRC / "data" / "recipes.json").read_text(encoding="utf-8"))
pack_names, recipes = rdata["products"], rdata["recipes"]
for i, r in enumerate(recipes, 1):
    r["num"] = f"{i:02d}"
    r["url"] = f"/recipes/{r['slug']}/"

# ---------------------------------------------------------------------------- markup builders
def product_card(p):
    chips = "".join(f'<span class="chip">{esc(c)}</span>' for c in p["chips"])
    return f"""  <article class="card reveal" data-cat="{esc(p['cat'])}" data-tone="{esc(p['tone'])}" data-id="{esc(p['id'])}" tabindex="0" aria-label="{esc(p['name'])}, view details">
    <div class="card-img"><span class="tag">{esc(p['tag'])}</span><img src="images/{p['id']}.webp" alt="Waffle Amour {esc(p['name'])} pack" loading="lazy" decoding="async"></div>
    <div class="card-body">
      <span class="eyebrow" style="font-size:.74rem">{esc(p['catName'])}</span>
      <h3>{esc(p['name'])}</h3>
      <p>{esc(p['desc'])}</p>
      <div class="meta">{chips}</div>
      <span class="more">View details {ARROW}</span>
    </div>
  </article>"""

def recipe_card(r):
    photo = (f'<img class="photo" src="images/recipes/thumb/{r["photo"]}" alt="" loading="lazy" decoding="async">'
             if r.get("photo") else "")
    return f"""<article class="r-card" data-cat="{esc(r['cat'])}">
    <a href="{r['url']}" class="r-visual{' has-photo' if photo else ''}" aria-label="{esc(r['title'])}">
      <span class="r-cat">{esc(r['cat'])}</span>
      {photo}
      <img class="pack" src="images/{r['product']}.webp" alt="" loading="lazy" decoding="async">
      <span class="r-num">{r['num']}</span>
    </a>
    <div class="r-body">
      <h3><a href="{r['url']}">{esc(r['title'])}</a></h3>
      <p>{esc(r['intro'])}</p>
      <div class="r-meta"><span>{ICO_TIME}{esc(r['time'])}</span><span>Serves {r['serves']}</span><a href="{r['url']}" class="r-go">View recipe →</a></div>
    </div>
  </article>"""

CTA = """  <section class="cta">
    <div class="wrap">
      <span class="eyebrow" style="color:var(--gold-2)">Find your favourite</span>
      <h2>Every recipe starts with a Waffle Amour</h2>
      <p>Liège sugar waffles, chocolate waffles, toasting waffles and dusted hearts, made with love.</p>
      <a href="index.html#range" class="btn btn-gold">Explore our waffles</a>
    </div>
  </section>"""

def recipes_list_main():
    cats = ["All"] + list(dict.fromkeys(r["cat"] for r in recipes))
    buttons = "".join(f'<button class="filter{" active" if i == 0 else ""}" data-cat="{esc(c)}" aria-pressed="{"true" if i == 0 else "false"}">{esc(c)}</button>'
                      for i, c in enumerate(cats))
    cards = "\n  ".join(recipe_card(r) for r in recipes)
    return f"""  <div id="listView">
    <section class="page-hero">
      <div class="wrap">
        <span class="eyebrow" style="color:var(--gold-2)">Recipes</span>
        <h1>Waffles, <em>your way</em>.</h1>
        <p>Easy ideas for breakfast, brunch, pudding and every celebration in between. Pick a recipe, grab a pack and make it yours.</p>
      </div>
    </section>
    <section class="listing">
      <div class="wrap">
        <div class="filters" id="filters" role="group" aria-label="Filter recipes">{buttons}</div>
        <div class="r-grid" id="recipeGrid">
  {cards}
        </div>
      </div>
    </section>
  </div>

{CTA}"""

def recipe_main(r):
    pname = pack_names[r["product"]]
    ing = "".join(f'<li{" class=\"opt\"" if "optional" in i else ""}>{esc(i)}</li>' for i in r["ing"])
    steps = "".join(f"<li><span>{esc(s)}</span></li>" for s in r["steps"])
    others = [x for x in recipes if x is not r]
    related = ([x for x in others if x["cat"] == r["cat"]] + [x for x in others if x["cat"] != r["cat"]])[:3]
    visual = (f'<div class="d-visual has-photo"><img class="photo" alt="{esc(r["title"])}, serving suggestion" src="images/recipes/{r["photo"]}">'
              f'<img class="pack" alt="" src="images/{r["product"]}.webp"></div>') if r.get("photo") else \
             f'<div class="d-visual"><img class="pack" alt="{esc(pname)} pack" src="images/{r["product"]}.webp"></div>'
    return f"""  <section class="detail" id="detailView">
    <div class="wrap">
      <nav class="crumb" aria-label="Breadcrumb"><a href="/recipes/">All recipes</a> / <span>{esc(r['title'])}</span></nav>
      <div class="d-grid">
        <div class="d-left">
          <div class="d-kicker">Recipe {r['num']} / {esc(r['cat'])}</div>
          <h1>{esc(r['title'])}</h1>
          <p class="d-intro">{esc(r['intro'])}</p>
          <div class="d-meta"><span>{esc(r['time'])}</span><i>·</i><span>Serves {r['serves']}</span></div>
          {visual}
          <div class="start">
            <img src="images/{r['product']}.webp" alt="{esc(pname)} pack">
            <div>
              <small>Start with</small>
              <b>{esc(pname)}</b>
              <a href="index.html#range" class="link">Explore our waffles</a>
            </div>
          </div>
        </div>
        <div class="d-right">
          <h2>What you'll need</h2>
          <ul class="ing">{ing}</ul>
          <h2>Make it yours</h2>
          <ol class="steps">{steps}</ol>
          <div class="twist"><b>A little twist</b><span>{esc(r['twist'])}</span></div>
          <div class="d-actions">
            <a href="/recipes/" class="link">Back to all recipes</a>
            <button onclick="print()">{ICO_PRINT}<span class="link">Print recipe</span></button>
          </div>
        </div>
      </div>
      <div class="more-recipes">
        <h2>You might also like</h2>
        <div class="r-grid">
  {chr(10).join("  " + recipe_card(x) for x in related)}
        </div>
      </div>
    </div>
  </section>

{CTA}"""

def recipe_jsonld(r):
    minutes = int(re.match(r"\d+", r["time"]).group())
    image = f"/images/recipes/{r['photo']}" if r.get("photo") else f"/images/{r['product']}.webp"
    data = {
        "@context": "https://schema.org", "@type": "Recipe",
        "name": r["title"], "description": r["intro"], "image": [abs_url(image)],
        "author": {"@type": "Organization", "name": "Waffle Amour"},
        "recipeCategory": r["cat"], "recipeCuisine": "British",
        "recipeYield": f"{r['serves']} serving{'s' if r['serves'] != 1 else ''}",
        "totalTime": f"PT{minutes}M",
        "keywords": f"waffle recipe, {r['title'].lower()}, Waffle Amour",
        "recipeIngredient": r["ing"],
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in r["steps"]],
    }
    return f'<script type="application/ld+json">{json_for_html(data)}</script>'

NOT_FOUND_MAIN = """  <section class="page-hero">
    <div class="wrap">
      <span class="eyebrow" style="color:var(--gold-2)">Page not found</span>
      <h1>This page has <em>crumbled</em>.</h1>
      <p>We couldn't find what you were looking for. Head back to the homepage or browse our waffle recipes.</p>
      <p style="margin-top:26px;display:flex;gap:14px;flex-wrap:wrap">
        <a href="index.html" class="btn btn-gold">Back to the homepage</a>
        <a href="recipes.html" class="btn btn-ghost" style="color:var(--gold-2)">Browse recipes</a>
      </p>
    </div>
  </section>"""

# ---------------------------------------------------------------------------- build
for generated in ["index.html", "404.html", "sitemap.xml", "robots.txt"]:
    (OUT / generated).unlink(missing_ok=True)
for folder in ["recipes", "css"]:
    shutil.rmtree(OUT / folder, ignore_errors=True)
shutil.copytree(SRC / "css", OUT / "css")

# Homepage
home = (SRC / "index.html").read_text(encoding="utf-8")
home = home.replace("<!--@PRODUCT_CARDS-->", "\n".join(product_card(p) for p in products))
home = home.replace("<!--@PRODUCTS_JSON-->", json_for_html(products))
write("index.html", finish(home, path="/",
    title="Waffle Amour | Authentic Belgian Waffles — UK's No.1 Sugar Waffle Brand",
    desc="Authentic Belgian waffles from Waffle Amour, the UK's No.1 sugar waffle brand: Liège sugar waffles, chocolate waffles and toasting waffles, plus easy waffle recipes.",
    og_title="Waffle Amour — UK's No.1 Sugar Waffle Brand",
    og_desc="Authentic Belgian waffles, made with love. Liège sugar waffles, chocolate waffles, toasting waffles and recipe ideas."))

shell = (SRC / "recipes.html").read_text(encoding="utf-8")

# Recipe list
write("recipes/index.html", finish(shell.replace("<!--@MAIN-->", recipes_list_main()), path="/recipes/",
    title="Waffle Recipes | Easy Ideas with Waffle Amour",
    desc="Easy waffle recipes for every occasion, from a Full English brunch to Eton mess, banoffee and sticky toffee. Made with Waffle Amour Belgian waffles."))

# One page per recipe
for r in recipes:
    photo = f"/images/recipes/{r['photo']}" if r.get("photo") else SHARE_IMAGE
    write(f"recipes/{r['slug']}/index.html", finish(shell.replace("<!--@MAIN-->", recipe_main(r)), path=r["url"],
        title=f"{r['title']} Recipe | Waffle Amour",
        desc=f"{r['intro']} Ready in {r['time']}, serves {r['serves']}.",
        og_title=f"{r['title']} | Waffle Amour recipe", og_image=photo, og_type="article",
        head_extra=recipe_jsonld(r)))

# 404
write("404.html", finish(shell.replace("<!--@MAIN-->", NOT_FOUND_MAIN), path="/404.html",
    title="Page not found | Waffle Amour",
    desc="Sorry, we couldn't find that page. Discover Waffle Amour Belgian waffles and recipes."))

# Sitemap + robots (only meaningful with a real domain)
if SITE_URL:
    urls = ["/", "/recipes/"] + [r["url"] for r in recipes]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{esc(abs_url(u))}</loc></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {abs_url('/sitemap.xml')}\n")
