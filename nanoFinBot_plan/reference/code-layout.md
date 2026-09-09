# nanoFinBot code layout

Nanotasks place code in these locations. Keep this stable — later nanotasks import from
earlier ones.

```
pyproject.toml            # deps + [project.scripts] nfb = "nanofinbot.cli:main"
install.py                # venv + deps + `pip install -e .` (cross-platform)
Dockerfile                # Alpine base, installs package, ENTRYPOINT ["nfb"]
.github/workflows/ghcr.yml# builds and pushes the GHCR image
nanofinbot/
  __init__.py
  cli.py          # `nfb` entrypoint + subcommands: setup, run, version
  config.py       # load/save config.json, platformdirs paths, atomic write
  db.py           # aiosqlite connection, schema init, repositories
  provider.py     # OpenAI-compatible client: text() and vision()
  parser.py       # rules-based parse + LLM categorization
  ocr.py          # photo download, Pillow preprocess, vision -> draft
  capture.py      # draft queue, save/edit/cancel, disable
  categories.py   # auto-create, rename
  reports.py      # PDF + CSV generation
  recurring.py    # recurring items + due-check
  bot.py          # aiogram Bot/Dispatcher, startup status, handlers
tests/
  conftest.py     # async fixtures, fake Telegram + fake provider
```

Conventions:
- Async throughout; `aiosqlite` for DB, `aiogram` for the bot.
- Config and data paths come from `platformdirs` (`user_config_dir`, `user_data_dir`,
  appname `nfb`).
- Amounts are integer minor units + ISO 4217 code (see `architecture.md` §2).
