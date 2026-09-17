# NLLB Translator — Multilingual Customer Support App

A simple end-to-end web app that wraps the assessment notebook's translation logic
(`facebook/nllb-200-distilled-600M`) behind a small Flask API with a single-page frontend.

It translates customer-support messages between **English ↔ French / Spanish / Hindi / Tamil**,
auto-detects the source language, and preserves technical identifiers (error codes, product names,
version numbers, emails, URLs, emoji) so they are never mistranslated.

## Project layout

```
nllb-translator-app/
├── backend/
│   ├── app.py           # Flask API + serves the frontend
│   └── translator.py    # reused notebook logic: load, detect, protect/restore, translate
├── frontend/
│   ├── index.html       # single-page UI
│   ├── style.css
│   └── script.js        # calls the API; XSS-safe rendering (textContent only)
├── requirements.txt
├── run.sh               # one-command start (venv + install + run)
├── Dockerfile           # containerized CPU build
├── .dockerignore
└── README.md
```

## Quick start (one command)

```bash
cd nllb-translator-app
./run.sh
```

Then open <http://localhost:8000>.

`run.sh` creates a virtual environment, installs dependencies, and starts the server.
The **first translation** downloads the model (~2.5 GB) — this is a one-time cost that is then cached.

> Change the port with `PORT=9000 ./run.sh`.

## Manual start (if you prefer)

```bash
cd nllb-translator-app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend && python app.py
```

## Run with Docker

```bash
cd nllb-translator-app
docker build -t nllb-translator .
# Mount a volume so the model download is reused across runs:
docker run --rm -p 8000:8000 -v nllb_hf_cache:/app/.hf_cache nllb-translator
```

Open <http://localhost:8000>.

## GPU (optional, much faster)

The app uses CUDA automatically if a compatible GPU + PyTorch build is present. To enable it,
install a CUDA build of PyTorch instead of the default CPU wheel, e.g.:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

`GET /api/health` reports whether it is running on `CPU` or `CUDA`.

## API

| Method | Path             | Body                                   | Returns |
|--------|------------------|----------------------------------------|---------|
| GET    | `/`              | —                                      | Web UI |
| GET    | `/api/health`    | —                                      | `{status, model_loaded, device, model}` |
| GET    | `/api/languages` | —                                      | `{languages:[{iso,name,nllb}]}` |
| POST   | `/api/translate` | `{text, target, source?}`              | `{ok, translation, detection, target_language, preserved}` |

`source` is optional — omit it to auto-detect. `target`/`source` accept an ISO code
(`fr`) or a name (`French`).

Example:

```bash
curl -s http://localhost:8000/api/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"My QuickShip order #INV-9932 is late & I got ERR-500 😤","target":"hi"}'
```

## How it works (pipeline)

`clean → detect source (Lingua) → protect identifiers → tokenize (SentencePiece) →
translate (NLLB, forced target language) → decode → restore identifiers`.

This is the same logic as the notebook, refactored into `backend/translator.py`.

## Notes

- Supported languages: English, French, Spanish, Hindi, Tamil.
- Input is capped at 4000 characters.
- The frontend renders all model output with `textContent` (no `innerHTML`), so translated
  text and preserved tokens cannot inject markup.
- Model and dependency versions are pinned in `requirements.txt` for reproducibility.
```
