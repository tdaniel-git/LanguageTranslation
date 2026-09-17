# Language Translation System — Complete Bundle

Everything for the Lexora AI NLP assessment, in one folder. Unzip and open in VS Code.

## Contents

```
language-translation-system/
├── Language_Translation_System_NLLB.ipynb          # Colab notebook (13 sections, NLLB-200)
├── Video_Script_Language_Translation_System.docx   # Explanation-video script (submission req. 7)
└── nllb-translator-app/                            # End-to-end web app (Flask + HTML/JS)
    ├── backend/   (app.py, translator.py)
    ├── frontend/  (index.html, style.css, script.js)
    ├── requirements.txt
    ├── run.sh                                       # one-command start
    ├── Dockerfile / .dockerignore
    └── README.md                                    # app-specific docs
```

## What each piece is

- **Notebook** — full walkthrough that produces the required output. Open in Google Colab
  (GPU runtime recommended) or in VS Code with the Jupyter extension.
- **Video script** — camera-ready narration covering approach, internals, and a dry run.
- **Web app** — reuses the notebook's exact translation logic behind a simple UI.
  See `nllb-translator-app/README.md` for full details.

## Run the web app (quick start)

```bash
cd language-translation-system/nllb-translator-app
./run.sh
```

Then open http://localhost:8000 . First translation downloads the model (~2.5 GB), then it's cached.

### Or with Docker

```bash
cd language-translation-system/nllb-translator-app
docker build -t nllb-translator .
docker run --rm -p 8000:8000 -v nllb_hf_cache:/app/.hf_cache nllb-translator
```

## Using in VS Code

1. Unzip, then File → Open Folder… → select `language-translation-system`.
2. Notebook: install the Python + Jupyter extensions, then open the `.ipynb`.
3. App: open a terminal in `nllb-translator-app` and run `./run.sh` (creates a venv, installs deps).

Requirements: Python 3.9–3.11. GPU optional but much faster (see the app README for the CUDA
PyTorch install command).
# LanguageTranslation
# LanguageTranslation
