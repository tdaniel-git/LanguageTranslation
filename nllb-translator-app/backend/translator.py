"""
Translation engine — reuses the exact logic from the assessment notebook.

Pipeline: clean -> detect source (Lingua) -> protect identifiers -> tokenize
-> translate (NLLB, forced target) -> decode -> restore identifiers.

Model: facebook/nllb-200-distilled-600M (loaded lazily, once).
"""
from __future__ import annotations

import re
import threading
import unicodedata

MODEL_NAME = "facebook/nllb-200-distilled-600M"

# ---------------------------------------------------------------- language map
# ISO 639-1  <->  NLLB (FLORES-200) codes. Single source of truth.
LANG_MAP = {
    "en": {"name": "English", "nllb": "eng_Latn"},
    "fr": {"name": "French",  "nllb": "fra_Latn"},
    "es": {"name": "Spanish", "nllb": "spa_Latn"},
    "hi": {"name": "Hindi",   "nllb": "hin_Deva"},
    "ta": {"name": "Tamil",   "nllb": "tam_Taml"},
}
NAME_TO_ISO = {v["name"].lower(): k for k, v in LANG_MAP.items()}
NAME_TO_ISO.update({k: k for k in LANG_MAP})


def to_iso(lang: str) -> str:
    """Accept 'fr', 'French', 'FRENCH' -> 'fr'. Raises on unsupported."""
    key = (lang or "").strip().lower()
    if key not in NAME_TO_ISO:
        raise ValueError(f"Unsupported language: {lang!r}. Supported: {list(LANG_MAP)}")
    return NAME_TO_ISO[key]


def supported_languages():
    """Return [{iso, name, nllb}] for the UI dropdown."""
    return [{"iso": k, "name": v["name"], "nllb": v["nllb"]} for k, v in LANG_MAP.items()]


# ---------------------------------------------------------------- cleaning
def _ensure_utf8(text) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _normalize_whitespace(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(text) -> str:
    text = _ensure_utf8(text)
    text = unicodedata.normalize("NFC", text)   # important for Devanagari / Tamil
    return _normalize_whitespace(text)


# ---------------------------------------------------------------- identifier protection
PRODUCT_NAMES = ["Lexora AI", "Lexora", "AcmeCloud", "PayPro", "QuickShip", "InvoiceX"]

_PATTERNS = [
    ("url",     re.compile(r"https?://\S+|www\.\S+")),
    ("email",   re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("errcode", re.compile(r"\b(?:0x[0-9A-Fa-f]+|(?:ERR|ERROR|ERRNO|CODE|E|HTTP)[-_ ]?\d{2,}|\d{3}\s?error)\b", re.I)),
    ("ticket",  re.compile(r"#\w[\w-]*")),
    ("version", re.compile(r"\bv?\d+\.\d+(?:\.\d+)*\b")),
    ("product", re.compile(r"\b(?:" + "|".join(re.escape(p) for p in sorted(PRODUCT_NAMES, key=len, reverse=True)) + r")\b")),
]

_EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF" "\U0001F900-\U0001F9FF" "\U0000FE00-\U0000FE0F" "]+"
)


def _placeholder(i: int) -> str:
    return f"PHOLDER{i}X"


def protect(text: str):
    """Replace identifiers/emoji with placeholders. Returns (masked_text, mapping)."""
    mapping = {}
    idx = 0

    def _sub(pattern):
        nonlocal idx, text

        def repl(m):
            nonlocal idx
            ph = _placeholder(idx)
            mapping[ph] = m.group(0)
            idx += 1
            return ph

        text = pattern.sub(repl, text)

    for _name, pat in _PATTERNS:
        _sub(pat)
    _sub(_EMOJI)
    return text, mapping


def restore(text: str, mapping: dict) -> str:
    """Put original identifiers back, tolerant to spacing/case the model may add."""
    for ph, original in mapping.items():
        num = re.search(r"\d+", ph).group(0)
        pat = re.compile(r"P\s*H\s*O\s*L\s*D\s*E\s*R\s*" + num + r"\s*X", re.I)
        text = pat.sub(lambda _m: original, text)
        text = text.replace(ph, original)
    return text


# ---------------------------------------------------------------- lazy singletons
_lock = threading.Lock()
_state = {"model": None, "tokenizer": None, "detector": None, "device": "cpu", "loaded": False}
CONFIDENCE_THRESHOLD = 0.55


def _build_detector():
    from lingua import Language, LanguageDetectorBuilder
    global _LINGUA_MAP
    _LINGUA_MAP = {
        Language.ENGLISH: "en",
        Language.FRENCH: "fr",
        Language.SPANISH: "es",
        Language.HINDI: "hi",
        Language.TAMIL: "ta",
    }
    return (LanguageDetectorBuilder
            .from_languages(*_LINGUA_MAP.keys())
            .with_preloaded_language_models()
            .build())


def load(verbose: bool = True):
    """Load the detector + NLLB model once (thread-safe). Safe to call repeatedly."""
    if _state["loaded"]:
        return
    with _lock:
        if _state["loaded"]:
            return
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        if verbose:
            print(f"[translator] loading {MODEL_NAME} on {device} ...", flush=True)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device).eval()

        _state.update(model=model, tokenizer=tokenizer,
                      detector=_build_detector(), device=device, loaded=True)
        if verbose:
            print("[translator] ready.", flush=True)


def is_loaded() -> bool:
    return _state["loaded"]


def device() -> str:
    return _state["device"]


# ---------------------------------------------------------------- detection
def detect_language(text: str) -> dict:
    load()
    text = clean_text(text)
    if not text:
        return {"iso": None, "name": None, "confidence": 0.0,
                "is_unknown": True, "reason": "empty input"}
    conf_values = _state["detector"].compute_language_confidence_values(text)
    if not conf_values:
        return {"iso": None, "name": None, "confidence": 0.0,
                "is_unknown": True, "reason": "no language matched"}
    best = conf_values[0]
    iso = _LINGUA_MAP[best.language]
    confident = best.value >= CONFIDENCE_THRESHOLD
    return {
        "iso": iso if confident else None,
        "name": LANG_MAP[iso]["name"] if confident else None,
        "confidence": round(float(best.value), 3),
        "is_unknown": not confident,
        "reason": None if confident else f"low confidence (<{CONFIDENCE_THRESHOLD})",
        "top_guess": LANG_MAP[iso]["name"],
    }


# ---------------------------------------------------------------- translate
MAX_INPUT_CHARS = 4000


def translate(text: str, target_language: str, source_language: str | None = None,
              num_beams: int = 4, max_new_tokens: int = 256) -> dict:
    """Translate `text` into `target_language`. Returns a JSON-serializable dict."""
    if text is None or not str(text).strip():
        return {"ok": False, "error": "Please enter a message to translate."}
    if len(text) > MAX_INPUT_CHARS:
        return {"ok": False, "error": f"Message too long (max {MAX_INPUT_CHARS} characters)."}

    try:
        tgt_iso = to_iso(target_language)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    load()
    import torch

    cleaned = clean_text(text)

    # source language: manual override or auto-detect
    if source_language:
        try:
            src_iso = to_iso(source_language)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        det = {"iso": src_iso, "name": LANG_MAP[src_iso]["name"],
               "confidence": 1.0, "is_unknown": False, "reason": "manual override"}
    else:
        det = detect_language(cleaned)

    if det["is_unknown"]:
        return {"ok": False, "error": "Could not confidently detect the source language.",
                "detection": det}

    if det["iso"] == tgt_iso:
        return {"ok": True, "translation": cleaned, "detection": det,
                "target_language": LANG_MAP[tgt_iso]["name"], "preserved": [],
                "note": "Source and target languages are the same."}

    src_code = LANG_MAP[det["iso"]]["nllb"]
    tgt_code = LANG_MAP[tgt_iso]["nllb"]

    masked, mapping = protect(cleaned)

    tokenizer, model = _state["tokenizer"], _state["model"]
    tokenizer.src_lang = src_code
    inputs = tokenizer(masked, return_tensors="pt", truncation=True, max_length=512).to(_state["device"])
    forced_bos = tokenizer.convert_tokens_to_ids(tgt_code)

    with torch.inference_mode():
        generated = model.generate(**inputs, forced_bos_token_id=forced_bos,
                                   num_beams=num_beams, max_new_tokens=max_new_tokens)
    decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
    final = _normalize_whitespace(restore(decoded, mapping))

    preserved = [v for v in mapping.values() if v in final]
    return {
        "ok": True,
        "translation": final,
        "detection": det,
        "source_language": det["name"],
        "target_language": LANG_MAP[tgt_iso]["name"],
        "preserved": preserved,
    }
