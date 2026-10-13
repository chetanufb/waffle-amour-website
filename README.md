# Waffle Amour website

Brand website for Waffle Amour: authentic Belgian waffles, made with love.

## Structure
| Path | What it is |
|---|---|
| `src/index.html` | Homepage template (edit this) |
| `src/recipes.html` | Shared page shell for the recipe list, each recipe page and the 404 page |
| `src/data/products.json` | The product range (names, descriptions, nutrition) |
| `src/data/recipes.json` | The 13 recipes |
| `src/css/` | Dark Chocolate and All-Light theme styles |
| `public/` | **The published site** — generated pages plus images, video and icons |
| `tools/build.py` | Generates the pages in `public/` from `src/` |

Every page has a light/dark toggle in the header (dark by default) that remembers the visitor's choice.
Each recipe has its own page at `/recipes/<recipe-name>/` with Recipe structured data.

## After editing anything in `src/`
```bash
python tools/build.py
```
Then commit and push; Netlify publishes `public/` automatically.

When the domain is live, set `SITE_URL` at the top of `tools/build.py` and rebuild: this adds
canonical links, full share-image addresses, `sitemap.xml` and `robots.txt`.

## Preview locally
```bash
python -m http.server 8765 --directory public
```
Then open http://localhost:8765/
