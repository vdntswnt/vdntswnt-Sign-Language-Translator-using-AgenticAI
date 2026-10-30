"""
app.py  —  Flask server, Ollama-first with silent gloss.py fallback
====================================================================
Pipeline:
  PRIMARY  → agent.py run_agent() drives Ollama LLM
               LLM uses gloss.py as an optional tool (get_gloss_suggestion)
  FALLBACK → if Ollama is unreachable, silently runs gloss.py directly

Quick start
-----------
    ollama pull llama3
    ollama serve          # keep running in a terminal tab
    python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, requests as req

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
WORDS_DIR     = os.path.join(BASE_DIR, '..', 'src', 'Words')
ALPHABETS_DIR = os.path.join(BASE_DIR, '..', 'src', 'Alphabets')

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)

# ── Auto-scan sign files ─────────────────────────────────────────────────────
# Reads the actual .js files from Words/ and Alphabets/ at startup.
# Adding a new .js file is all you need — no code changes required.

def _scan_signs(directory: str) -> set:
    """Return a set of uppercase token names from .js files in directory."""
    if not os.path.isdir(directory):
        return set()
    return {
        f[:-3].upper()                          # strip .js, uppercase
        for f in os.listdir(directory)
        if f.endswith('.js') and not f.startswith('_')
    }

# Scanned once at startup — use get_available_words() to refresh if needed
_WORD_SIGNS  = _scan_signs(WORDS_DIR)
_ALPHA_SIGNS = _scan_signs(ALPHABETS_DIR)

print(f"[Signs] Loaded {len(_WORD_SIGNS)} word signs: {sorted(_WORD_SIGNS)}")
print(f"[Signs] Loaded {len(_ALPHA_SIGNS)} alpha signs: {sorted(_ALPHA_SIGNS)}")

def get_available_words() -> set:
    """Re-scan Words/ — call this if you add files while server is running."""
    global _WORD_SIGNS
    _WORD_SIGNS = _scan_signs(WORDS_DIR)
    return _WORD_SIGNS

def get_available_alphas() -> set:
    """Re-scan Alphabets/ — call this if you add files while server is running."""
    global _ALPHA_SIGNS
    _ALPHA_SIGNS = _scan_signs(ALPHABETS_DIR)
    return _ALPHA_SIGNS

# ── File-existence helpers ────────────────────────────────────────────────────

def word_js_exists(word: str) -> bool:
    return word.upper() in _WORD_SIGNS

def alpha_js_exists(letter: str) -> bool:
    return letter.upper() in _ALPHA_SIGNS

def expand_word(word: str) -> list:
    w = word.upper()
    if word_js_exists(w):
        return [{"token": w, "folder": "words"}]
    return [
        {"token": ch, "folder": "alphabets" if alpha_js_exists(ch) else "none"}
        for ch in w if ch.isalpha()
    ]

# ── Import pipelines ──────────────────────────────────────────────────────────
from agent import register_helpers, run_agent, fix_missing_tokens, INTENT_LABELS
from gloss import ISignOrchestrator
from storage import init_db, save_session, load_session, delete_session, save_feedback, get_bad_gloss, get_feedback_stats

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()

_orchestrator = ISignOrchestrator()

# Register all helpers including gloss pipeline
register_helpers(
    word_js_exists,
    alpha_js_exists,
    expand_word,
    gloss_pipeline=_orchestrator.get_sequence,   # exposed as LLM tool
)

# ── Inject scanned sign list into agent for dynamic FAST_PROMPT ──────────────
import agent as _agent_module
_agent_module._AVAILABLE_WORD_SIGNS = _WORD_SIGNS
print(f"[App] Injected {len(_WORD_SIGNS)} word signs into agent prompt")

# ── Gloss fallback (used when Ollama is down) ─────────────────────────────────

def _run_gloss_fallback(text: str, mode: str) -> dict:
    """
    Silently runs gloss.py pipeline + fix_missing_tokens.
    Called when Ollama is unreachable.
    """
    print(f"[Fallback] Ollama unreachable — using gloss.py for: '{text}'")
    final_gloss, resolved_tokens, text_info = _orchestrator.get_sequence(text)

    MARKERS    = {"QUESTION", "EXCLAMATION"}
    sign_tokens = [t for t in resolved_tokens if t not in MARKERS]
    sequence   = fix_missing_tokens(sign_tokens)

    intent_key     = text_info.get("intent", "statement")
    is_question    = text_info.get("is_question", False)
    is_exclamation = text_info.get("is_exclamation", False)

    tags = []
    if is_question:    tags.append("Question")
    if is_exclamation: tags.append("Exclamation")
    tags.append("Fingerspell" if mode == "letter" else "Word Mode")

    display_gloss = " ".join(s["token"] for s in sequence)

    return {
        "success":        True,
        "input_text":     text,
        "clean_text":     text_info.get("clean_text", text),
        "intent_key":     intent_key,
        "intent":         INTENT_LABELS.get(intent_key, intent_key.replace("_", " ").title()),
        "gloss":          display_gloss,
        "gloss_words":    [s["token"] for s in sequence],
        "sequence":       sequence,
        "is_question":    is_question,
        "is_exclamation": is_exclamation,
        "has_ellipsis":   text_info.get("has_ellipsis", False),
        "mode":           mode,
        "tags":           tags,
        "total_signs":    len(sequence),
        "status":         f"Generated {len(sequence)} sign(s) via gloss fallback (Ollama offline)",
        "pipeline":       "gloss_fallback",
    }


# ── Static serving ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


# ── /translate  (Ollama primary, gloss fallback) ──────────────────────────────

@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "No JSON data received"}), 400

        text       = str(data.get("text", "")).strip()
        mode       = str(data.get("mode", "word")).strip().lower()
        session_id = data.get("session_id")

        if not text:
            return jsonify({"success": False, "error": "No text provided"}), 400
        if mode not in {"word", "letter"}:
            mode = "word"

        # ── Check corrections — has user thumbs-downed this before? ───────────
        bad_gloss = get_bad_gloss(text)
        if bad_gloss:
            print(f"[Memory] Found previous correction for: '{text}' (bad: '{bad_gloss}')")

        try:
            # PRIMARY: Ollama LLM agent
            result = run_agent(text, mode=mode, session_id=session_id, bad_gloss=bad_gloss)

            # ── Persist session to SQLite ─────────────────────────────────────
            if result.get("session_id"):
                from agent import _sessions
                s = _sessions.get(result["session_id"])
                if s:
                    save_session(s.session_id, s.history)

            return jsonify(result), 200 if result["success"] else 422

        except (req.exceptions.ConnectionError, req.exceptions.Timeout):
            # FALLBACK: gloss.py (silent — no error shown to user)
            result = _run_gloss_fallback(text, mode)
            return jsonify(result), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


# ── /feedback ────────────────────────────────────────────────────────────────

@app.route("/feedback", methods=["POST"])
def feedback():
    try:
        data       = request.get_json(silent=True) or {}
        session_id = data.get("session_id", "unknown")
        input_text = str(data.get("input_text", "")).strip()
        gloss      = str(data.get("gloss", "")).strip()
        rating     = int(data.get("rating", 0))  # 1 = thumbs up, -1 = thumbs down

        if not input_text or not gloss or rating not in (1, -1):
            return jsonify({"success": False, "error": "Missing input_text, gloss or rating"}), 400

        save_feedback(session_id, input_text, gloss, rating)
        msg = "Thanks for the feedback!" if rating == 1 else "Got it — we'll avoid that gloss next time."
        return jsonify({"success": True, "message": msg, "rating": rating})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── /session ──────────────────────────────────────────────────────────────────

@app.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    from agent import _sessions
    s = _sessions.get(session_id)
    if not s:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"session_id": s.session_id, "turns": len(s.history), "history": s.history})

@app.route("/session/<session_id>", methods=["DELETE"])
def clear_session(session_id):
    from agent import _sessions
    _sessions.pop(session_id, None)
    delete_session(session_id)
    return jsonify({"cleared": True, "session_id": session_id})


# ── /agent/config ─────────────────────────────────────────────────────────────

@app.route("/agent/config", methods=["GET"])
def agent_config_get():
    import agent
    return jsonify({
        "model":       agent.OLLAMA_MODEL,
        "base_url":    agent.OLLAMA_BASE,
        "max_steps":   agent.MAX_STEPS,
        "temperature": agent.TEMPERATURE,
    })

@app.route("/agent/config", methods=["POST"])
def agent_config_set():
    import agent
    data = request.get_json(silent=True) or {}
    if "model"       in data: agent.OLLAMA_MODEL  = data["model"]
    if "base_url"    in data: agent.OLLAMA_BASE   = data["base_url"]
    if "max_steps"   in data: agent.MAX_STEPS     = int(data["max_steps"])
    if "temperature" in data: agent.TEMPERATURE   = float(data["temperature"])
    return jsonify({"updated": True})


# ── /signs ───────────────────────────────────────────────────────────────────

@app.route("/signs", methods=["GET"])
def list_signs():
    """Show all currently loaded sign files."""
    return jsonify({
        "word_signs":  sorted(_WORD_SIGNS),
        "alpha_signs": sorted(_ALPHA_SIGNS),
        "word_count":  len(_WORD_SIGNS),
        "alpha_count": len(_ALPHA_SIGNS),
    })

@app.route("/signs/reload", methods=["POST"])
def reload_signs():
    """
    Re-scan Words/ and Alphabets/ without restarting the server.
    Call this after dropping in new .js files.
    Also updates the FAST_PROMPT in agent.py with the new sign list.
    """
    words  = get_available_words()
    alphas = get_available_alphas()

    # Update agent.py's FAST_PROMPT sign list dynamically
    import agent as _agent
    _agent._AVAILABLE_WORD_SIGNS = words
    print(f"[Signs] Reloaded — {len(words)} word signs, {len(alphas)} alpha signs")
    print(f"[Signs] Word signs: {sorted(words)}")

    return jsonify({
        "reloaded":    True,
        "word_signs":  sorted(words),
        "alpha_signs": sorted(alphas),
        "word_count":  len(words),
        "alpha_count": len(alphas),
    })


# ── /health ───────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    import agent
    ollama_ok = False
    try:
        r = req.get(f"{agent.OLLAMA_BASE}/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        pass

    try:
        word_count  = len([f for f in os.listdir(WORDS_DIR)     if f.endswith('.js')])
        alpha_count = len([f for f in os.listdir(ALPHABETS_DIR) if f.endswith('.js')])
    except Exception:
        word_count = alpha_count = -1

    return jsonify({
        "flask":       "ok",
        "ollama":      "ok" if ollama_ok else "unreachable — gloss.py fallback active",
        "model":       agent.OLLAMA_MODEL,
        "pipeline":    "ollama-primary / gloss-fallback",
        "memory":      get_feedback_stats(),
        "word_signs":  word_count,
        "alpha_signs": alpha_count,
    })


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n  Open      →  http://127.0.0.1:5000")
    print(f"  Health    →  http://127.0.0.1:5000/health")
    print(f"  Words     →  {WORDS_DIR}")
    print(f"  Alphabets →  {ALPHABETS_DIR}")
    print(f"\n  PRIMARY   →  Ollama LLM (llama3) via agent.py")
    print(f"  FALLBACK  →  gloss.py (silent, if Ollama is offline)")
    print(f"\n  ⚠  Run 'ollama serve' for full agentic mode.\n")
    app.run(debug=True, host="127.0.0.1", port=5000)