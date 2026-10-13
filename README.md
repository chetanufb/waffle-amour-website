# Waffle Amour website

Brand website for Waffle Amour: authentic Belgian waffles, made with love.

## Structure
| Path | What it is |
|---|---|
| `index.html`, `recipes.html` | Source pages (edit these) |
| `dark/` | Built site that opens in Dark Chocolate mode, plus `theme-choc.css` |
| `light/` | Built site that opens in All-Light mode, plus `theme-light.css` |
| `images/`, `videos/` | Shared media (packs, logos, recipe photos + `recipes/thumb/` card versions) |
| `tools/build_themes.py` | Rebuilds `dark/` and `light/` from the source pages |

Both built versions include a light/dark toggle in the header that remembers the visitor's choice.

## After editing a source page
```bash
python tools/build_themes.py
```

## Preview locally
```bash
python -m http.server 8765
```
Then open http://localhost:8765/dark/ or http://localhost:8765/light/
