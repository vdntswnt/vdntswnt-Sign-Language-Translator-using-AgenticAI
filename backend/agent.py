"""
agent.py  —  Ollama-first agentic ISL/ASL translation
======================================================
Ollama is the primary translation brain.
gloss.py is available as a tool the LLM can call for rule-based suggestions.
app.py silently falls back to gloss.py if Ollama is unreachable.

Dependencies
------------
    pip install requests

Local LLM setup (one-time)
--------------------------
    ollama pull llama3
    ollama serve        # runs on http://localhost:11434
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field

import requests

# ── spaCy NER ─────────────────────────────────────────────────────────────────
try:
    import spacy as _spacy
    _nlp = _spacy.load("en_core_web_sm")
    print("[NER] spaCy en_core_web_sm loaded successfully")
except Exception as _e:
    _nlp = None
    print(f"[NER] spaCy not available: {_e} — NER tool will be skipped")

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_BASE  = "http://localhost:11434"
OLLAMA_MODEL = "qwen3.5"
MAX_STEPS    = 4
TEMPERATURE  = 0.2

# ── Synonym map ───────────────────────────────────────────────────────────────

# ── Available sign files (from src/Words/) ───────────────────────────────────
# DEAF, HE, HELLO, HOME, HOWAREYOU, MYNAMEIS, NAMASTE, SHE, SORRY,
# THANKYOU, TIME, YOU
# Alphabets: A-Z all available for fingerspelling

SYNONYM_MAP: dict[str, list[str]] = {
    # Time-related → TIME
    "HOUR":       ["TIME"],
    "CLOCK":      ["TIME"],
    "NIGHT":      ["TIME"],
    "MORNING":    ["TIME"],
    "EVENING":    ["TIME"],
    "AFTERNOON":  ["TIME"],
    "LATE":       ["TIME"],
    "EARLY":      ["TIME"],
    "WHEN":       ["TIME"],
    "NOW":        ["TIME"],
    "TODAY":      ["TIME"],
    "TOMORROW":   ["TIME"],
    "YESTERDAY":  ["TIME"],

    # Pronouns → HE / SHE / YOU
    "HIM":        ["HE"],
    "HIS":        ["HE"],
    "MAN":        ["HE"],
    "BOY":        ["HE"],
    "HER":        ["SHE"],
    "HERS":       ["SHE"],
    "WOMAN":      ["SHE"],
    "GIRL":       ["SHE"],
    "THEY":       ["HE"],
    "YOUR":       ["YOU"],
    "YOURS":      ["YOU"],
    "PERSON":     ["HE"],
    "SOMEONE":    ["HE"],

    # Greetings → HELLO / NAMASTE
    "HI":         ["HELLO"],
    "HEY":        ["HELLO"],
    "GREET":      ["HELLO"],
    "WELCOME":    ["NAMASTE"],
    "GOODBYE":    ["HELLO"],
    "BYE":        ["HELLO"],

    # Apologies → SORRY
    "APOLOGIZE":  ["SORRY"],
    "APOLOGIES":  ["SORRY"],
    "EXCUSE":     ["SORRY"],
    "PARDON":     ["SORRY"],
    "FORGIVE":    ["SORRY"],
    "REGRET":     ["SORRY"],
    "OOPS":       ["SORRY"],

    # Thanks → THANKYOU
    "THANKS":     ["THANKYOU"],
    "THANK":      ["THANKYOU"],
    "GRATEFUL":   ["THANKYOU"],
    "APPRECIATE": ["THANKYOU"],

    # Home/place → HOME (residence only, NOT movement)
    "HOUSE":      ["HOME"],
    "RESIDENCE":  ["HOME"],
    # Movement words — no sign file, fingerspell
    "COME":       ["COME"],   # COME.js exists
    "GO":         [],
    "WALK":       [],
    "RUN":        [],
    "MOVE":       [],
    "TRAVEL":     [],
    "VISIT":      [],
    "LIVE":       [],
    "STAY":       [],
    # Verbs — map to closest available sign or empty to fingerspell
    "SAY":        [],
    "SAID":       [],
    "ASK":        [],
    "ASKED":      [],
    "TELL":       [],
    "TOLD":       [],
    "WANT":       [],
    "NEED":       [],
    "EAT":        [],
    "DRINK":      [],
    "WORK":       [],
    "STUDY":      [],
    "PLAY":       [],
    "KNOW":       [],
    "THINK":      [],
    "FEEL":       [],
    "TIMED":      ["TIME"],   # TIMED → use TIME sign
    "TIME":       ["TIME"],   # TIME.js exists
    "BUT":        [],
    "AND":        [],
    # New sign files available
    "GOODBYE":    ["BYE"],
    "FAREWELL":   ["BYE"],
    "SEE YOU":    ["BYE"],
    "QUICKLY":    ["FAST"],
    "QUICK":      ["FAST"],
    "SPEED":      ["FAST"],
    "SLOWLY":     ["SLOW"],
    "GRADUAL":    ["SLOW"],
    "DISTANCE":   ["FAR"],
    "AWAY":       ["FAR"],
    "SCRUB":      ["CLEAN"],
    "WASH":       ["CLEAN"],
    "TIDY":       ["CLEAN"],
    "DRUG":       ["MEDICINE"],
    "PILL":       ["MEDICINE"],
    "TABLET":     ["MEDICINE"],
    "MEDICATION": ["MEDICINE"],
    "ARRIVE":     ["COME"],
    "APPROACHING":["COME"],
    "NEAR":       [],
    "CLOSE":      [],   # CLOSE.js coming soon

    # Common objects — no sign file, fingerspell as single token
    "LIGHT":      [],
    "LIGHTS":     ["LIGHT"],
    "OFF":        [],
    "ON":         [],
    "FAN":        [],
    "DOOR":       [],
    "WINDOW":     [],
    "PHONE":      [],
    "WATER":      [],
    "FOOD":       [],
    "SCHOOL":     [],
    "HOSPITAL":   [],
    "PLEASE":     [],

    # Identity → MYNAMEIS / HOWAREYOU
    "NAME":       ["MYNAMEIS"],
    "CALLED":     ["MYNAMEIS"],

    # Deaf/hearing
    "HEARING":    ["DEAF"],
    "MUTE":       ["DEAF"],

    # IT / THIS / THAT → fingerspell (no sign file, keep short)
    "THIS":       [],
    "THAT":       [],
    "IT":         [],
    "IS":         [],
    "AT":         [],
    "WHO":        [],   # no WHO.js — will fingerspell W-H-O
}

# ── Session memory ────────────────────────────────────────────────────────────

@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history:    list[dict] = field(default_factory=list)
    context:    dict = field(default_factory=dict)

_sessions: dict[str, Session] = {}

def get_or_create_session(session_id: str | None) -> Session:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    s = Session(session_id=session_id or str(uuid.uuid4()))
    _sessions[s.session_id] = s
    return s


# ── Helpers injected from app.py ──────────────────────────────────────────────

_word_js_exists_fn  = None
_alpha_js_exists_fn = None
_gloss_pipeline_fn  = None   # gloss.py orchestrator.get_sequence

def register_helpers(word_exists, alpha_exists, expand_word, gloss_pipeline=None):
    global _word_js_exists_fn, _alpha_js_exists_fn, _gloss_pipeline_fn
    _word_js_exists_fn  = word_exists
    _alpha_js_exists_fn = alpha_exists
    _gloss_pipeline_fn  = gloss_pipeline


# ── Tool implementations ──────────────────────────────────────────────────────

def _check_word_sign(word: str) -> dict:
    word = word.upper()
    return {"exists": bool(_word_js_exists_fn and _word_js_exists_fn(word)), "word": word}

def _check_fingerspell(word: str) -> dict:
    word = word.upper()
    missing = [ch for ch in word if ch.isalpha() and
               not (_alpha_js_exists_fn and _alpha_js_exists_fn(ch))]
    return {"can_spell": len(missing) == 0, "missing_letters": missing, "word": word}

def _find_synonym_sign(word: str) -> dict:
    word = word.upper()
    for syn in SYNONYM_MAP.get(word, []):
        if _word_js_exists_fn and _word_js_exists_fn(syn):
            return {"found": True, "original": word, "replacement": syn}
    return {"found": False, "original": word, "replacement": None}

def _get_gloss_suggestion(sentence: str) -> dict:
    """Calls gloss.py rule-based pipeline as a tool the LLM can consult."""
    if not _gloss_pipeline_fn:
        return {"available": False, "reason": "gloss pipeline not registered"}
    try:
        final_gloss, resolved_tokens, text_info = _gloss_pipeline_fn(sentence)
        return {
            "available":       True,
            "suggested_gloss": final_gloss,
            "tokens":          resolved_tokens,
            "intent":          text_info.get("intent", "statement"),
            "is_question":     text_info.get("is_question", False),
            "is_exclamation":  text_info.get("is_exclamation", False),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}

def _detect_entities(sentence: str) -> dict:
    """
    Runs spaCy NER on the input sentence.
    Returns a list of detected entities so the LLM knows what to fingerspell.
    Entity types: PERSON, GPE (location), ORG, DATE, TIME, NORP, FAC, LOC
    """
    if _nlp is None:
        return {"available": False, "entities": [], "reason": "spaCy not loaded"}
    try:
        doc = _nlp(sentence)
        entities = [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            for ent in doc.ents
        ]
        fingerspell_words = [ent["text"].upper() for ent in entities
                             if ent["label"] in ("PERSON", "GPE", "LOC", "ORG", "FAC", "NORP")]
        print(f"[NER] detected: {entities}")
        return {
            "available":         True,
            "entities":          entities,
            "fingerspell_these": fingerspell_words,   # LLM should fingerspell these
        }
    except Exception as e:
        return {"available": False, "entities": [], "reason": str(e)}


# ── Domain knowledge base ────────────────────────────────────────────────────

DOMAIN_RULES: dict[str, dict] = {
    "HOME": {
        "keywords":  ["light", "lights", "fan", "door", "window", "kitchen",
                      "room", "house", "home", "water", "food", "tv", "phone",
                      "off", "on", "clean", "cook", "sleep", "wake"],
        "critical":  ["LIGHT", "FAN", "DOOR", "WINDOW", "WATER", "FOOD",
                      "OFF", "ON", "SLEEP", "COOK", "CLEAN"],
        "drop":      ["CAN", "COULD", "PLEASE", "TURN", "SWITCH", "JUST",
                      "THAT", "THIS", "THE", "A", "AN"],
        "sign_files": ["CLEAN", "HOME", "TIME"],
    },
    "MEDICAL": {
        "keywords":  ["doctor", "hospital", "medicine", "pain", "sick", "health",
                      "nurse", "clinic", "fever", "headache", "injury", "appointment"],
        "critical":  ["DOCTOR", "PAIN", "MEDICINE", "HOSPITAL", "SICK",
                      "FEVER", "NURSE", "HELP"],
        "drop":      ["CAN", "PLEASE", "NEED", "WANT", "GOING", "VISIT"],
        "sign_files": ["MEDICINE", "SORRY", "HELP"],
    },
    "SCHOOL": {
        "keywords":  ["school", "teacher", "class", "homework", "study", "exam",
                      "student", "lesson", "book", "learn", "college", "university"],
        "critical":  ["TEACHER", "SCHOOL", "HOMEWORK", "EXAM", "STUDY", "BOOK"],
        "drop":      ["CAN", "PLEASE", "NEED", "WANT", "GOING", "DO"],
    },
    "TRAVEL": {
        "keywords":  ["bus", "train", "station", "airport", "ticket", "travel",
                      "go", "come", "where", "direction", "map", "road"],
        "critical":  ["BUS", "TRAIN", "STATION", "AIRPORT", "TICKET", "WHERE"],
        "drop":      ["CAN", "PLEASE", "NEED", "WANT", "TAKE"],
    },
    "SOCIAL": {
        "keywords":  ["hello", "hi", "meet", "friend", "name", "nice", "sorry",
                      "thank", "goodbye", "bye", "how", "you", "welcome"],
        "critical":  ["HELLO", "NAME", "MEET", "FRIEND", "SORRY", "THANK"],
        "drop":      ["IT", "IS", "WAS", "VERY", "REALLY"],
    },
    "GENERAL": {
        "keywords":  [],
        "critical":  [],
        "drop":      ["CAN", "COULD", "PLEASE", "JUST", "REALLY", "VERY"],
    },
}


def _detect_domain(sentence: str) -> dict:
    """
    Detects the domain of the sentence and returns:
    - domain name
    - critical words (never drop these)
    - words to drop (politeness markers, redundant verbs for this domain)

    This gives the LLM context-aware dropping rules instead of generic ones.
    """
    sentence_lower = sentence.lower()
    words          = set(sentence_lower.split())

    best_domain    = "GENERAL"
    best_score     = 0

    for domain, rules in DOMAIN_RULES.items():
        if domain == "GENERAL":
            continue
        score = sum(1 for kw in rules["keywords"] if kw in sentence_lower)
        if score > best_score:
            best_score  = score
            best_domain = domain

    rules = DOMAIN_RULES[best_domain]

    # Find which critical words appear in this sentence
    sentence_upper    = sentence.upper()
    relevant_critical = [w for w in rules["critical"]
                         if w in sentence_upper or w.lower() in sentence_lower]
    relevant_drop     = [w for w in rules["drop"]
                         if w in sentence_upper or w.lower() in sentence_lower]

    print(f"[Domain] detected: {best_domain} (score={best_score})")
    print(f"[Domain] critical={relevant_critical} drop={relevant_drop}")

    return {
        "domain":    best_domain,
        "score":     best_score,
        "critical":  relevant_critical,   # LLM MUST keep these
        "drop":      relevant_drop,       # LLM SHOULD drop these
        "all_critical": rules["critical"],
        "all_drop":     rules["drop"],
    }


def _build_sequence(gloss_words: list[str]) -> dict:
    print(f"[build_sequence] received: {gloss_words}")
    # Flatten in case LLM passes nested lists or dicts
    flat = []
    for item in gloss_words:
        if isinstance(item, str):
            flat.append(item.upper().strip())
        elif isinstance(item, dict):
            t = item.get("token") or item.get("word") or ""
            if t: flat.append(t.upper().strip())
    flat = [w for w in flat if w]
    print(f"[build_sequence] tokens to resolve: {flat}")
    sequence = fix_missing_tokens(flat)
    print(f"[build_sequence] resolved sequence: {[s['token'] for s in sequence]}")
    return {"sequence": sequence, "total": len(sequence)}


# ── Token fixer ───────────────────────────────────────────────────────────────

def fix_missing_tokens(resolved_tokens: list[str]) -> list[dict]:
    """
    Verifies each gloss token against sign files.
    Patches missing tokens: synonym swap → fingerspell → skip.
    Returns [{token, folder}, ...]
    """
    sequence = []
    for token in resolved_tokens:
        tok = token.upper()

        # 1. Direct sign file
        if _word_js_exists_fn and _word_js_exists_fn(tok):
            sequence.append({"token": tok, "folder": "words"})
            continue

        # 2. Synonym swap
        syn = _find_synonym_sign(tok)
        if syn["found"]:
            print(f"[Agent] '{tok}' → synonym '{syn['replacement']}'")
            sequence.append({"token": syn["replacement"], "folder": "words"})
            continue

        # 3. Full fingerspell
        spell = _check_fingerspell(tok)
        if spell["can_spell"]:
            print(f"[Agent] '{tok}' → fingerspelling")
            for ch in tok:
                if ch.isalpha():
                    sequence.append({"token": ch, "folder": "alphabets"})
            continue

        # 4. Partial fingerspell
        if any(ch.isalpha() and _alpha_js_exists_fn and _alpha_js_exists_fn(ch) for ch in tok):
            print(f"[Agent] '{tok}' → partial fingerspelling")
            for ch in tok:
                if ch.isalpha():
                    folder = "alphabets" if (_alpha_js_exists_fn and _alpha_js_exists_fn(ch)) else "none"
                    sequence.append({"token": ch, "folder": folder})
            continue

        # 5. Skip
        print(f"[Agent] WARNING: '{tok}' skipped — no sign, synonym, or fingerspelling.")

    # ── Deduplicate consecutive identical tokens ───────────────────────────
    # Prevents double signs when LLM outputs e.g. "TIMED TIME" or "GO GO"
    deduped = []
    for item in sequence:
        if not deduped or item["token"] != deduped[-1]["token"]:
            deduped.append(item)
        else:
            print(f"[Agent] Deduplicated consecutive '{item['token']}'")

    return deduped


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "check_word_sign",
        "description": (
            "Check whether a whole-word sign animation (.js file) exists for a given word. "
            "Always call this before including a word in your final gloss. "
            "Returns {exists: bool, word: str}."
        ),
        "parameters": {"word": {"type": "string", "description": "Uppercase English word to check"}},
    },
    {
        "name": "find_synonym_sign",
        "description": (
            "If check_word_sign returns false, try this to find a synonym that has a sign file. "
            "Returns {found: bool, original: str, replacement: str | null}."
        ),
        "parameters": {"word": {"type": "string", "description": "Word that is missing a sign"}},
    },
    {
        "name": "check_fingerspell",
        "description": (
            "Check if a word can be fingerspelled letter by letter. "
            "Use as a last resort when no sign or synonym exists. "
            "Returns {can_spell: bool, missing_letters: [str], word: str}."
        ),
        "parameters": {"word": {"type": "string", "description": "Word to check for fingerspelling"}},
    },
    {
        "name": "detect_domain",
        "description": (
            "Detect the domain of the sentence (HOME, MEDICAL, SCHOOL, TRAVEL, SOCIAL, GENERAL). "
            "Returns {domain, critical: [words to KEEP], drop: [words to DROP]}. "
            "Call this to get context-aware dropping rules for smarter ISL gloss."
        ),
        "parameters": {"sentence": {"type": "string", "description": "The original English sentence"}},
    },
    {
        "name": "detect_entities",
        "description": (
            "Run NER (Named Entity Recognition) on the input text to detect "
            "people names, places, organizations and other proper nouns. "
            "Returns {entities: [{text, label}], fingerspell_these: [str]}. "
            "Call this FIRST so you know which words must be fingerspelled."
        ),
        "parameters": {"sentence": {"type": "string", "description": "The original English sentence"}},
    },
    {
        "name": "get_gloss_suggestion",
        "description": (
            "Get a rule-based ISL gloss suggestion from the built-in grammar engine. "
            "Useful as a starting point — you can accept, modify, or override it. "
            "Returns {suggested_gloss: str, tokens: [str], intent: str, is_question: bool, is_exclamation: bool}."
        ),
        "parameters": {"sentence": {"type": "string", "description": "The original English sentence"}},
    },
    {
        "name": "build_sequence",
        "description": (
            "Finalise the translation. Call this once you are satisfied with the complete gloss list. "
            "Verifies each token and builds the animation sequence. "
            "Returns {sequence: [{token, folder}], total: int}."
        ),
        "parameters": {
            "gloss_words": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Final ordered list of uppercase gloss tokens"
            }
        },
    },
    {
        "name": "clarify_input",
        "description": "Ask the user a clarifying question when input is too ambiguous to translate.",
        "parameters": {"question": {"type": "string", "description": "Question to ask the user"}},
    },
]

TOOL_DESCRIPTIONS = "\n".join(f"- {t['name']}: {t['description']}" for t in TOOLS)

def _run_tool(name: str, params: dict) -> dict:
    if name == "check_word_sign":     return _check_word_sign(params.get("word", ""))
    if name == "find_synonym_sign":   return _find_synonym_sign(params.get("word", ""))
    if name == "check_fingerspell":   return _check_fingerspell(params.get("word", ""))
    if name == "detect_domain":         return _detect_domain(params.get("sentence", ""))
    if name == "detect_entities":        return _detect_entities(params.get("sentence", ""))
    if name == "get_gloss_suggestion":return _get_gloss_suggestion(params.get("sentence", ""))
    if name == "build_sequence":      return _build_sequence(params.get("gloss_words", []))
    if name == "clarify_input":       return {"clarification_needed": True, "question": params.get("question", "")}
    return {"error": f"Unknown tool: {name}"}


# ── Ollama LLM call ───────────────────────────────────────────────────────────

def _ollama_chat(messages: list[dict], system_prompt: str) -> str:
    """Raises requests.exceptions.ConnectionError if Ollama is unreachable."""
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream":   False,
        "options":  {"temperature": TEMPERATURE},
        "think":    False,   # disable thinking mode (qwen3.5, deepseek-r1, etc.)
    }
    resp = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are an expert Indian Sign Language (ISL) translation agent.
Convert English text into ISL gloss in EXACTLY 2 STEPS:

STEP 1: Call build_sequence immediately with your ISL gloss tokens.
STEP 2: Set tool=done with the result.

ISL grammar rules:
- Drop articles (a, an, the), copulas (is, am, are), auxiliaries
- Topic-comment order: object before action ("I eat food" → FOOD ME EAT)  
- Questions: move question word to END ("Where are you going?" → YOU GO WHERE)
- Time words go FIRST (TODAY, NOW, TOMORROW, MORNING)
- Negation: NOT after the sign ("I don't know" → ME KNOW NOT)

Available tools:
{TOOL_DESCRIPTIONS}

STRICT RULES:
- Respond ONLY with valid JSON. No prose. No markdown. No think tags.
- NEVER call check_word_sign — build_sequence handles verification automatically.
- Keep gloss SHORT: 2-5 tokens max.
- Never include QUESTION or EXCLAMATION as tokens.

EXAMPLE for "who are you?":
Step 1: {{"thought": "ISL: YOU WHO", "tool": "build_sequence", "params": {{"gloss_words": ["YOU", "WHO"]}}, "gloss_so_far": ["YOU", "WHO"]}}
Step 2: {{"thought": "done", "tool": "done", "final_gloss": "YOU WHO", "sequence": [...], "intent": "question_who", "is_question": true, "is_exclamation": false, "total_signs": 2}}

EXAMPLE for "why is it wrong?":
Step 1: {{"thought": "ISL: IT WRONG WHY", "tool": "build_sequence", "params": {{"gloss_words": ["IT", "WRONG", "WHY"]}}, "gloss_so_far": ["IT", "WRONG", "WHY"]}}
Step 2: {{"thought": "done", "tool": "done", "final_gloss": "IT WRONG WHY", "sequence": [...], "intent": "question_why", "is_question": true, "is_exclamation": false, "total_signs": 3}}
"""

# ── Intent label map ──────────────────────────────────────────────────────────

INTENT_LABELS = {
    "statement":        "Statement",
    "question_what":    "What Question",
    "question_who":     "Who Question",
    "question_where":   "Where Question",
    "question_how":     "How Question",
    "question_when":    "When Question",
    "question_why":     "Why Question",
    "question_general": "Question",
    "greeting":         "Greeting",
    "greeting_excited": "Excited Greeting",
    "request":          "Request",
    "command":          "Command",
    "exclamation":      "Exclamation",
    "incomplete":       "Incomplete",
    "thanking":         "Thanking",
    "apologising":      "Apologising",
}


# ── Fast single-shot agent ───────────────────────────────────────────────────
#
# Instead of a slow multi-step loop, we:
# 1. Run gloss.py instantly for the base translation (< 1ms)
# 2. Make ONE fast LLM call to improve the gloss (intent + reordering)
# 3. fix_missing_tokens patches any missing signs
# Total: ~3-5 seconds instead of 2-3 minutes

# ── Dynamic sign list — updated by app.py after file scan ───────────────────
_AVAILABLE_WORD_SIGNS: set = set()


def _get_fast_prompt() -> str:
    """Returns FAST_PROMPT with current sign file list. Called at translation time."""
    sign_list = ", ".join(sorted(_AVAILABLE_WORD_SIGNS)) if _AVAILABLE_WORD_SIGNS         else "DEAF, HELLO, HOME, TIME, BYE, COME, CLEAN, FAR, FAST, SLOW, SORRY, MEDICINE"
    return f"""You are an ISL gloss expert with NER capability. Convert English to Indian Sign Language gloss.

AVAILABLE SIGN FILES (only use these as whole-word tokens):
{sign_list}

PRONOUN RULES — CRITICAL:
- I / ME / MY → always keep as ME in gloss (fingerspelled M-E, no sign file but NEVER drop it)
- YOU / YOUR  → YOU (sign file exists)
- HE / HIM    → HE  (sign file exists)
- SHE / HER   → SHE (sign file exists)
- NEVER drop the subject pronoun from a sentence

ISL GRAMMAR RULES — FOLLOW STRICTLY:
1. DROP ALWAYS — these words are NEVER signed in ISL, drop them completely:
   - Articles: a, an, the
   - Copulas: is, am, are, was, were, be, been, being
   - Auxiliaries: will, shall, would, should, could, can, did, does, do, had, has, have
   - Desire auxiliaries ONLY when followed by TO+verb: WANT TO, NEED TO, LIKE TO, WISH TO, HOPE TO, TRY TO, PLAN TO — drop the desire verb AND the TO, keep the main verb
   - Infinitive marker: TO (only when it follows a desire verb as above)
   - NEVER drop WANT/WISH/HOPE when they are the MAIN verb of the sentence (e.g. "he wished for food" → HE WISH FOOD, "there is hope" → HOPE)
   - Filler words: ALSO, JUST, VERY, REALLY, QUITE, RATHER, EVEN, STILL, ALREADY
   - Conjunctions: AND, BUT, OR, SO, BECAUSE, THAT, WHICH, WHO (when used as conjunction)
   RULE: In ISL, desire/emotion is shown through FACIAL EXPRESSION not a sign. So "I want to eat" = ME EAT (face shows wanting), "she needs to rest" = SHE REST
2. DROP: IT, THIS, THAT, AT, IN, ON, FOR — no sign files, omit entirely
3. KEEP: ME, YOU, HE, SHE — always keep subject pronouns
4. QUESTION WORD ALWAYS LAST: HOW, WHO, WHAT, WHERE, WHY, WHEN must be the FINAL token
5. TIME WORDS FIRST: use TIME for hour, clock, night, morning, now, today
6. SUBJECT before VERB before OBJECT
7. HOME = place of living only (not movement). COME, GO, WALK = fingerspell as-is
8. Words NOT in sign files get fingerspelled automatically — just include them as tokens

EXAMPLES (study these carefully):
"how are you?"             → YOU HOW              (drop 'are', YOU first, HOW last)
"who are you?"             → YOU WHO              (drop 'are', YOU first, WHO last)
"where are you going?"     → YOU GO WHERE         (drop 'are', GO fingerspelled, WHERE last)
"what is the time?"        → TIME WHAT            (TIME first, WHAT last)
"why is it wrong?"         → WRONG WHY            (topic first, WHY last)
"she is at home"           → SHE HOME             (drop 'is at', HOME=residence)
"I am sorry"               → SORRY                (SORRY sign covers full meaning)
"thank you"                → THANKYOU
"hello, who are you?"      → HELLO YOU WHO
"he is deaf"               → HE DEAF
"what is your name?"       → YOU NAME WHAT        (YOUR→YOU, NAME fingerspelled, WHAT last)
"where do you live?"       → YOU LIVE WHERE       (LIVE fingerspelled, WHERE last)
"who is he?"               → HE WHO
"I said come here!"                          → ME SAY COME HERE
"I want to go"                               → ME GO
"I come to Mumbai"                           → ME COME MUMBAI
"Riya come to Mumbai"                        → RIYA COME MUMBAI
"I timed it"                                 → ME TIME
"he asked how are you"                       → HE ASK HOWAREYOU
"my name is Riya"                            → ME NAME RIYA
"I live in Mumbai"                           → ME LIVE MUMBAI
"she lives in Delhi"                         → SHE LIVE DELHI
"can you turn off the lights?"               → LIGHT OFF YOU      (topic first: LIGHT OFF, then YOU)
"can you turn off the lights at that time?"  → LIGHT OFF TIME YOU (topic: LIGHT OFF, time: TIME, subject: YOU)
"turn off the fan"                           → FAN OFF             (topic first, no subject needed for commands)
"turn on the light"                          → LIGHT ON            (topic first)
"please close the door for me"               → YOU DOOR ME
"I need to go to school"                     → ME GO SCHOOL
"what time is it?"                           → TIME WHAT
"she wants to eat something"                 → SHE EAT
"I want to rest"                             → ME REST          (drop WANT, TO)
"I want to go"                               → ME GO            (drop WANT, TO)
"I want to sleep"                            → ME REST          (SLEEP→REST synonym)
"she wants to come"                          → SHE COME         (drop WANTS, TO)
"he wants to eat"                            → HE EAT           (drop WANTS, TO)

SIMPLIFICATION RULE — CRITICAL:
When a sentence contains many words, apply these steps in order:
1. Remove ALL words from the DROP list above first
2. Keep: SUBJECT + main VERB/NOUN + OBJECT + QUESTION WORD (if any)
3. Maximum 4 tokens for most sentences
4. Never fingerspell desire verbs (WANT, NEED, LIKE) — they are dropped entirely
5. Never output a long chain of fingerspelled letters

PATTERN RECOGNITION — always apply these transformations:
"[subject] want/need/like/wish/hope/try TO [verb]"   → [SUBJECT] [VERB]          (desire aux + TO = drop both)
"[subject] want/need/like/wish/hope/try TO [verb] [object]" → [SUBJECT] [VERB] [OBJECT]
"[subject] wished/wanted/hoped for [noun]"           → [SUBJECT] WISH/WANT [NOUN] (main verb = keep it)
"there is [noun]" / "[noun] exists"                  → [NOUN]                     (existential = just the noun)
"[subject] is/am/are [adjective]"                    → [SUBJECT] [ADJECTIVE]
"[subject] is/am/are going to [verb]"                → [SUBJECT] [VERB]
"can/could/should [subject] [verb]?"                 → [SUBJECT] [VERB] (question word at end)

Respond with ONLY this JSON, no prose, no markdown:
{{"gloss": "TOKEN1 TOKEN2", "intent": "statement|question_why|question_who|question_what|question_where|question_how|question_when|question_general|greeting|thanking|apologising|exclamation|command|request", "is_question": false, "is_exclamation": false}}"""


# ── Pre-processor: drop desire auxiliaries before LLM sees them ──────────────
# Handles: "I want to rest" → "I rest", "she needs to come" → "she come"
# Only drops when pattern is: [desire_verb] TO [main_verb]
# Keeps desire verbs when they are the main verb: "he wants food" stays

import re as _re

_DESIRE_AUX = r'(want|wants|wanted|need|needs|needed|like|likes|liked|wish|wished|hope|hoped|hopes|try|tries|tried|plan|plans|planned|decide|decides|decided|going)'

def _preprocess_text(text: str) -> str:
    """
    Drops desire auxiliaries when followed by TO + verb.
    "I want to rest"     → "I rest"
    "she needs to come"  → "she come"
    "he wants food"      → "he wants food"  (no TO+verb, keep)
    """
    # Pattern: desire_verb + optional whitespace + "to" + whitespace + verb
    pattern = _DESIRE_AUX + r'\s+to\s+'
    result = _re.sub(pattern, '', text, flags=_re.IGNORECASE).strip()
    # Clean up double spaces
    result = _re.sub(r'\s+', ' ', result).strip()
    if result != text:
        print(f"[Preprocess] '{text}' → '{result}'")
    return result


def run_agent(
    text: str,
    mode: str = "word",
    session_id: str | None = None,
    bad_gloss: str | None = None,
) -> dict:
    """
    Fast single-shot translation:
    gloss.py draft → one LLM call to improve → fix_missing_tokens → done.
    Raises ConnectionError if Ollama is down (app.py catches and falls back).
    bad_gloss: previously thumbs-downed gloss for this input — agent avoids it.
    """
    # ── Preprocess: drop desire auxiliaries before anything else ─────────────
    text = _preprocess_text(text)

    session = get_or_create_session(session_id)

    # ── Load persisted history from SQLite if session is new ─────────────────
    if not session.history:
        try:
            from storage import load_session
            saved = load_session(session.session_id)
            if saved:
                session.history = saved
                print(f"[Agent] Loaded {len(saved)} turns from SQLite for session {session.session_id[:8]}")
        except ImportError:
            pass

    session.history.append({"role": "user", "content": text})

    # ── Step 1: gloss.py instant draft ───────────────────────────────────────
    draft_gloss = text.upper()
    draft_intent = "statement"
    draft_is_q = False
    draft_is_ex = False

    if _gloss_pipeline_fn:
        try:
            final_gloss, resolved_tokens, text_info = _gloss_pipeline_fn(text)
            MARKERS = {"QUESTION", "EXCLAMATION"}
            clean_tokens = [t for t in resolved_tokens if t not in MARKERS]
            draft_gloss   = " ".join(clean_tokens)
            draft_intent  = text_info.get("intent", "statement")
            draft_is_q    = text_info.get("is_question", False)
            draft_is_ex   = text_info.get("is_exclamation", False)
            print(f"[Agent] gloss.py draft: {draft_gloss}")
        except Exception as e:
            print(f"[Agent] gloss.py draft failed: {e}")

    # ── Step 1b: Domain detection + NER ─────────────────────────────────────
    domain_result = _detect_domain(text)
    domain        = domain_result["domain"]
    critical      = domain_result["critical"]
    drop          = domain_result["drop"]

    domain_context = f"\nDomain: {domain}"
    if critical:
        domain_context += f"\nCRITICAL words (never drop): {critical}"
    if drop:
        domain_context += f"\nDROP these words (redundant in {domain} domain): {drop}"

    ner_result  = _detect_entities(text)
    ner_context = ""
    if ner_result["available"] and ner_result["entities"]:
        fs = ner_result["fingerspell_these"]
        ner_context = f"\nNER detected — fingerspell these words: {fs}" if fs else ""
        print(f"[Agent] NER entities: {ner_result['entities']}")

    # ── Step 2: single LLM call to improve ───────────────────────────────────
    bad_gloss_context = f"\nIMPORTANT: The user previously rejected this gloss: \"{bad_gloss}\" — do NOT produce it again." if bad_gloss else ""
    user_msg = f'English: "{text}"{domain_context}{ner_context}{bad_gloss_context}\nRule-based draft: "{draft_gloss}"\nUse domain rules to decide what to keep/drop. Fingerspell detected names/places.'

    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": _get_fast_prompt()},
            {"role": "user",   "content": user_msg},
        ],
        "stream":  False,
        "think":   False,
        "options": {"temperature": 0.1, "num_predict": 100},
    }

    improved_gloss  = draft_gloss
    intent_key      = draft_intent
    is_question     = draft_is_q
    is_exclamation  = draft_is_ex

    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=30)
        resp.raise_for_status()
        raw = resp.json()["message"]["content"]
        print(f"[Agent] LLM raw: {raw[:120]}")

        # Strip think tags
        clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        clean = re.sub(r"```json|```", "", clean).strip()

        # Parse JSON
        m = re.search(r"\{.*\}", clean, re.DOTALL)
        if m:
            data = json.loads(m.group())
            improved_gloss = data.get("gloss", draft_gloss).upper().strip()
            intent_key     = data.get("intent", draft_intent)
            is_question    = data.get("is_question", draft_is_q)
            is_exclamation = data.get("is_exclamation", draft_is_ex)
            print(f"[Agent] LLM improved: {improved_gloss}")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Let app.py handle the fallback
        raise
    except Exception as e:
        print(f"[Agent] LLM improvement failed, using draft: {e}")

    # ── Step 3: fix_missing_tokens ────────────────────────────────────────────
    MARKERS = {"QUESTION", "EXCLAMATION"}
    tokens   = [t for t in improved_gloss.split() if t not in MARKERS]

    # Deduplicate — remove consecutive identical tokens the LLM may repeat
    deduped = []
    for tok in tokens:
        if not deduped or tok != deduped[-1]:
            deduped.append(tok)
    tokens = deduped

    sequence = fix_missing_tokens(tokens)
    print(f"[Agent] final sequence: {[s['token'] for s in sequence]}")

    # ── Self-correct: empty sequence → fall back to gloss.py draft ───────────
    if not sequence and draft_gloss:
        print(f"[Agent] SELF-CORRECT: LLM gloss gave empty sequence, retrying with draft: {draft_gloss}")
        draft_tokens = [t for t in draft_gloss.split() if t not in MARKERS]
        sequence     = fix_missing_tokens(draft_tokens)
        improved_gloss = draft_gloss
        print(f"[Agent] self-corrected sequence: {[s['token'] for s in sequence]}")

    # ── Self-correct: still empty → fingerspell the raw input words ──────────
    if not sequence:
        print(f"[Agent] SELF-CORRECT: draft also empty, fingerspelling raw input")
        raw_words = [w.upper() for w in text.split() if w.isalpha()]
        sequence  = fix_missing_tokens(raw_words)
        improved_gloss = " ".join(raw_words)

    # ── Warn if everything is fingerspelled (no word signs at all) ────────────
    all_fingerspelled = all(s["folder"] == "alphabets" for s in sequence) if sequence else False
    if all_fingerspelled:
        print(f"[Agent] WARNING: no word signs found, all tokens fingerspelled")

    tags = []
    if is_question:      tags.append("Question")
    if is_exclamation:   tags.append("Exclamation")
    if all_fingerspelled: tags.append("Fingerspelled")
    tags.append("Fingerspell" if mode == "letter" else "Word Mode")

    display_gloss = " ".join(s["token"] for s in sequence)
    session.history.append({"role": "assistant", "content": f"[Gloss: {display_gloss}]"})

    return {
        "success":        True,
        "input_text":     text,
        "clean_text":     text,
        "intent_key":     intent_key,
        "intent":         INTENT_LABELS.get(intent_key, intent_key.replace("_", " ").title()),
        "gloss":          display_gloss,
        "gloss_words":    [s["token"] for s in sequence],
        "sequence":       sequence,
        "is_question":    is_question,
        "is_exclamation": is_exclamation,
        "has_ellipsis":   False,
        "mode":           mode,
        "tags":           tags,
        "total_signs":    len(sequence),
        "status":         f"Generated {len(sequence)} sign(s) via fast agent",
        "session_id":     session.session_id,
        "steps_taken":    1,
        "agent_thoughts": [{"step": 1, "thought": f"draft={draft_gloss} → improved={display_gloss}"}],
        "pipeline":       "ollama_fast",
    }