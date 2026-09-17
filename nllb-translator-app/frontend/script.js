"use strict";

// ---- element refs ----
const $ = (id) => document.getElementById(id);
const inputEl = $("input");
const targetEl = $("target");
const sourceEl = $("source");
const btn = $("translateBtn");
const charCount = $("charCount");
const modelStatus = $("modelStatus");

const resultPanel = $("resultPanel");
const outputEl = $("output");
const detectedChip = $("detectedChip");
const targetChip = $("targetChip");
const preservedBlock = $("preservedBlock");
const preservedList = $("preservedList");

const errorPanel = $("errorPanel");
const errorMsg = $("errorMsg");

// ---- helpers ----
function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function setStatus(kind, text) {
  modelStatus.className = "status status--" + kind;
  modelStatus.textContent = text; // textContent => XSS-safe
}

function showError(msg) {
  hide(resultPanel);
  errorMsg.textContent = msg;       // textContent => XSS-safe
  show(errorPanel);
}

// ---- populate language dropdowns ----
async function loadLanguages() {
  try {
    const res = await fetch("/api/languages");
    const data = await res.json();
    const langs = (data.languages || []);
    for (const lang of langs) {
      const opt = document.createElement("option");
      opt.value = lang.iso;
      opt.textContent = lang.name;
      targetEl.appendChild(opt);
      const opt2 = opt.cloneNode(true);
      sourceEl.appendChild(opt2);
    }
    // sensible default target: French
    if ([...targetEl.options].some((o) => o.value === "fr")) targetEl.value = "fr";
  } catch (e) {
    showError("Could not load language list. Is the backend running?");
  }
}

// ---- poll model status until ready ----
async function pollHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.model_loaded) {
      setStatus("ready", `Model ready · running on ${String(data.device).toUpperCase()}`);
      return;
    }
    setStatus("loading", "Loading model (first run downloads ~2.5GB)…");
  } catch (e) {
    setStatus("error", "Backend not reachable.");
    return;
  }
  setTimeout(pollHealth, 2500);
}

// ---- char counter ----
inputEl.addEventListener("input", () => {
  charCount.textContent = `${inputEl.value.length} / 4000`;
});

// ---- translate ----
async function doTranslate() {
  const text = inputEl.value.trim();
  const target = targetEl.value;
  const source = sourceEl.value; // "" => auto

  hide(errorPanel);
  if (!text) { showError("Please enter a message to translate."); return; }

  btn.disabled = true;
  const originalLabel = btn.textContent;
  btn.innerHTML = '<span class="spinner"></span>Translating…';

  try {
    const res = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, target, source }),
    });
    const data = await res.json();

    if (!data.ok) {
      showError(data.error || "Translation failed.");
      return;
    }

    renderResult(data);
  } catch (e) {
    showError("Network error contacting the backend.");
  } finally {
    btn.disabled = false;
    btn.textContent = originalLabel;
  }
}

function renderResult(data) {
  hide(errorPanel);

  // translated text (XSS-safe)
  outputEl.textContent = data.translation || "";

  // detected source language chip
  if (data.detection && data.detection.name) {
    const conf = data.detection.confidence;
    const isManual = data.detection.reason === "manual override";
    detectedChip.textContent = isManual
      ? `Source: ${data.detection.name} (manual)`
      : `Detected: ${data.detection.name} (${Math.round(conf * 100)}% confidence)`;
    show(detectedChip);
  } else {
    hide(detectedChip);
  }

  // target chip
  if (data.target_language) {
    targetChip.textContent = `→ ${data.target_language}`;
    show(targetChip);
  } else {
    hide(targetChip);
  }

  // preserved identifiers demo
  preservedList.replaceChildren();
  const preserved = data.preserved || [];
  if (preserved.length) {
    for (const token of preserved) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = token;        // textContent => XSS-safe
      preservedList.appendChild(chip);
    }
    show(preservedBlock);
  } else {
    hide(preservedBlock);
  }

  show(resultPanel);
}

btn.addEventListener("click", doTranslate);
inputEl.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") doTranslate();
});

// ---- init ----
loadLanguages();
pollHealth();
