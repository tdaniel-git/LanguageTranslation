"""
Flask backend for the NLLB Translator.

Serves the single-page frontend and a small JSON API:
  GET  /               -> the web UI
  GET  /api/health     -> {status, model_loaded, device}
  GET  /api/languages  -> supported languages for the dropdown
  POST /api/translate  -> {text, target, source?} -> translation + detection + preserved

Run:  python backend/app.py   (listens on 0.0.0.0:$PORT, default 8000)
"""
import os
import threading

from flask import Flask, jsonify, request, send_from_directory

import translator

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

app = Flask(__name__, static_folder=None)

# Warm up the model in a background thread so the first request isn't blocked
# by the (one-time) download/load. Requests before it's ready still work — they
# just trigger a synchronous load via translator.load().
threading.Thread(target=lambda: translator.load(verbose=True), daemon=True).start()


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def static_files(filename):
    # Only serve known static assets from the frontend folder.
    if filename in ("style.css", "script.js"):
        return send_from_directory(FRONTEND_DIR, filename)
    return ("Not found", 404)


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": translator.is_loaded(),
        "device": translator.device(),
        "model": translator.MODEL_NAME,
    })


@app.get("/api/languages")
def languages():
    return jsonify({"languages": translator.supported_languages()})


@app.post("/api/translate")
def translate():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    target = data.get("target", "")
    source = data.get("source") or None  # optional manual override

    if not isinstance(text, str) or not isinstance(target, str):
        return jsonify({"ok": False, "error": "Invalid request body."}), 400

    result = translator.translate(text, target_language=target, source_language=source)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # threaded=True so health checks respond while a translation is running.
    app.run(host="0.0.0.0", port=port, threaded=True)
