# Hackaday.io Exporter

Python utility that mirrors a Hackaday.io project into a Hugo page bundle. The exporter pulls the project overview, project logs (chronological order), downloads referenced media (with detected image extensions), and rewrites everything as Markdown that Blowfish/Hugo can consume.

## Requirements

- Python 3.9+
- `requests`
- `beautifulsoup4`

Install the dependencies however you prefer. For example:

```bash
python -m pip install --upgrade pip
python -m pip install --requirement requirements.txt
```

## Usage

```bash
python -m HaDio_exporter.exporter <project-url> [--output-dir content/projects] [--force]
```

- `project-url`: canonical Hackaday.io project URL (`https://hackaday.io/project/<id>-<slug>`)
- `--output-dir`: target directory for the Hugo bundles (defaults to `content/projects/`)
- `--force`: overwrite the bundle if the slug already exists

Example:

```bash
python -m HaDio_exporter.exporter \
  https://hackaday.io/project/203763-deriving-1-hz-from-candle-flame-oscillations \
  --output-dir content/projects
```

## Output

- Creates `content/projects/<slug>/index.md` with TOML front matter and a flat Markdown body that concatenates the project sections followed by a `## Project Logs` section.
- Downloads all referenced images, GIFs, and other assets into the same bundle directory with ASCII-safe filenames.
- Produces raw `<img>` tags for GIFs so Blowfish skips image processing, and shortcodes for YouTube embeds.

## Notes

- Non-ASCII characters are transliterated; historic spellings can be preserved manually via Hugo aliases if needed.
- The script relies on the public Hackaday.io markup. Significant theme/layout changes upstream may require tweaks to the selectors in `exporter.py`.
- Run the Hugo production build after importing to catch missing assets or formatting regressions.
