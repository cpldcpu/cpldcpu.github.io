# Repository Guidelines

## Project Structure & Module Organization
This site uses Hugo with the Blowfish theme. `content/` holds page bundles such as `content/blog/<year>/<month>/<slug>/index.md` with co-located assets. Layout overrides live in `layouts/`, pipeline assets in `assets/`, static pass-through files in `static/`, and environment-specific overrides in `config/`. Leave `themes/blowfish` untouched and update it through Git submodule commands when needed.

## Build, Test, and Development Commands
- `hugo server -D --navigateToChanged`: live preview with drafts enabled.
- `HUGO_CACHEDIR=$(pwd)/.hugo_cache hugo --panicOnWarning --gc --minify`: production build, aborting on warnings and cleaning the asset cache.
- `hugo new content/blog/my-post/index.md`: scaffold a compliant bundle via the default archetype.

## Coding Style & Naming Conventions
Use TOML front matter, sentence-case titles, and lowercase, hyphenated slugs (`ring-oscillator-clock`). Wrap Markdown paragraphs near 100 characters and prefer Markdown; use Blowfish shortcodes only when needed. Templates and SCSS use two-space indentation, while JSON/YAML data in `data/` should keep lowercase keys.

## Testing Guidelines
Before a pull request, run the production build command above, then spot-check the generated `public/` pages you touched. Call out manual verification (browser checks, embedded demos) in the PR description. For interactive snippets, sanity-check behavior with JavaScript disabled.

## Commit & Pull Request Guidelines
Keep commit subjects imperative and under 72 characters (`chore: sync blowfish submodule`). Separate unrelated changes. PRs should outline the intent, link issues when available, include screenshots for visual tweaks, and mention configuration toggles reviewers must flip.

## Configuration & Theme Updates
Document edits to `config/_default/` first (especially `hugo.toml`, menus, params) and mirror only the needed values in the root `hugo.toml` when required. Upgrade Blowfish via `git submodule update --remote themes/blowfish`, summarise upstream release notes, and spot-check sample pages after updating. Summary snippets rely on `summaryLength = 80` in `config/_default/hugo.toml`; keep that value aligned with the front-matter `summary` fields.

## Legacy Blog Import
Use the WordPress.com API (`https://public-api.wordpress.com/wp/v2/sites/cpldcpu.com/posts`) to fetch legacy entries. Create bundles under `content/blog/<year>/<month>/<slug>/` and set front matter `url` to the original permalink plus an alias for the numeric `/?p=` link. Convert HTML to Markdown with `pandoc` or a custom script, then tidy quotes, code spans, and links by hand. Download media into the bundle with their original filenames; copy the first image reference to `featured.*` so Blowfish treats it as the hero, add a concise ASCII-only `summary`, ensure section headings start at `##`, and keep slugs/URLs ASCII with aliases for historic non-ASCII paths. Purged legacy `<!--more-->` tags; do not add them again—`summaryLength` handles excerpts. When downloading media, ensure the response is the actual binary (retry the original URL if the CDN returns HTML). If a post ends up with fewer than two section headings, set `showTableOfContents: false` in its front matter so the floating TOC stays hidden. Leave it enabled otherwise. Rebuild galleries with the Blowfish `{{< gallery >}}` shortcode and `<img>` tags with proper CSS classes for layout control. Use classes like `grid-w50` for side-by-side images, `grid-w33` for three-column layouts, etc. Example: `<img src="image.jpg" class="grid-w50" />`. After each import, rerun the production build to catch missing assets. Run `pandoc --lua-filter scripts/pandoc-wp-gallery.lua --wrap=none -t gfm` so WordPress galleries convert into Blowfish `{{< gallery >}}` blocks with `<img>` tags automatically, then rewrite any remaining internal links to use site-relative paths (strip the `https://cpldcpu.com` origin). Jetpack tiled galleries (`wp-block-jetpack-tiled-gallery`) do not convert automatically; strip their wrapper divs and rebuild an explicit `{{< gallery >}}` block with the extracted `<img>` sources and appropriate `grid-w*` classes. Animated GIFs should be embedded with raw `<img>` tags (not Markdown images) so Blowfish skips image processing that otherwise times out.

## Link Hygiene
Replace `wp.me` or other shortlinks with site-relative permalinks so internal references survive domain migration. Resolve each target once and note the mapping alongside the migrated post.

## Site Navigation & Archive
Keep the header menu in `config/_default/menus.en.toml` up to date. The `/archive/` page relies on `layouts/shortcodes/archive-list.html`; if sections change, update that shortcode so it still lists posts newest-first.

## Non-ASCII Legacy
Legacy URLs and titles sometimes included non-ASCII characters (e.g., µ). Normalize slugs and canonical `url` fields to ASCII, then add aliases for the original forms so redirects keep working. Keep front-matter values ASCII; if you want a special character, add an alias that matches the original permalink.


## Git Ignore
Keep build artifacts out of version control: `public/`, `resources/`, `.hugo_cache/`, `.hugo_build.lock`, `.DS_Store`, and IDE folders are listed in `.gitignore`.
