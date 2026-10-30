import re
from typing import Dict, List
import nltk
from nltk import pos_tag, word_tokenize

# Uncomment these once if running for first time:
# nltk.download("punkt")
# nltk.download("averaged_perceptron_tagger_eng")
# nltk.download("punkt_tab")


# ── AGENT 1: Text Understanding ───────────────────────────────────────────────
class TextUnderstandAgent:
    def process(self, text: str) -> Dict:
        text = text.strip()

        has_question    = text.endswith("?")
        has_exclamation = text.endswith("!")
        has_ellipsis    = text.endswith("...")

        clean_text = re.sub(r"[^\w\s]", "", text).lower().strip()

        intent = "statement"

        if has_question or any(
            w in clean_text.split() for w in ["what", "who", "where", "how", "when", "why"]
        ):
            if   "what"  in clean_text: intent = "question_what"
            elif "who"   in clean_text: intent = "question_who"
            elif "where" in clean_text: intent = "question_where"
            elif "how"   in clean_text: intent = "question_how"
            elif "when"  in clean_text: intent = "question_when"
            elif "why"   in clean_text: intent = "question_why"
            else:                       intent = "question_general"

        elif has_exclamation:
            if any(w in clean_text for w in ["hello", "hi", "hey", "namaste"]):
                intent = "greeting_excited"
            elif any(w in clean_text for w in ["stop", "no", "wait"]):
                intent = "command"
            else:
                intent = "exclamation"

        elif any(w in clean_text for w in ["thank you", "thanks", "thank u"]):
            intent = "thanking"

        elif any(w in clean_text for w in ["sorry", "apolog"]):
            intent = "apologising"

        elif any(w in clean_text for w in ["hello", "hi", "hey", "namaste"]):
            intent = "greeting"

        elif any(w in clean_text for w in ["please", "can you", "could you"]):
            intent = "request"

        elif has_ellipsis:
            intent = "incomplete"

        return {
            "clean_text":     clean_text,
            "original_text":  text,
            "intent":         intent,
            "is_question":    has_question,
            "is_exclamation": has_exclamation,
            "has_ellipsis":   has_ellipsis,
        }


# ── AGENT 2: Gloss Translator ─────────────────────────────────────────────────
class GlossTranslator:
    def __init__(self):
        self.stopwords = {
            "am", "is", "are", "was", "were", "be", "being", "been",
            "have", "has", "had",
            "will", "shall", "would", "should",
            "can", "could", "may", "might", "must",
            "a", "an", "the",
            "of", "by", "as",
            "and", "or", "but", "so", "because", "if", "than", "that",
            "which", "while",
            "just", "very", "really", "also",
        }

        self.pronouns = {
            "i":    "ME",
            "me":   "ME",
            "my":   "MY",
            "mine": "MY",
            "you":  "YOU",
            "your": "YOUR",
            "he":   "HE",
            "him":  "HE",
            "his":  "HE",
            "she":  "SHE",
            "her":  "SHE",
            "hers": "SHE",
            "they": "THEY",
            "we":   "WE",
            "our":  "OUR",
            "it":   "IT",
            "its":  "ITS",
        }

        self.verb_map = {
            "going":   "GO",   "went":   "GO",   "goes":   "GO",
            "coming":  "COME", "came":   "COME",
            "doing":   "DO",   "done":   "DO",   "did":    "DO",
            "been":    "BE",
            "having":  "HAVE",
            "eating":  "EAT",  "ate":    "EAT",
            "seeing":  "SEE",  "saw":    "SEE",
            "saying":  "SAY",  "said":   "SAY",
            "wanting": "WANT", "wanted": "WANT",
            "needs":   "NEED", "needed": "NEED",
            "likes":   "LIKE", "liked":  "LIKE",
            "helping": "HELP", "helped": "HELP",
        }

        self.special_rules = {
            "i am fine":              "ME FINE",
            "i am deaf":              "ME DEAF",
            "i love you":             "ME LOVE YOU",
            "where are you going":    "YOU GO WHERE",
            "where do you live":      "YOU LIVE WHERE",
            "how old are you":        "YOU AGE HOW",
            "what is this":           "THIS WHAT",
            "who are you":            "YOU WHO",
            "where have you been":    "YOU WHERE",
            "are you there":          "YOU THERE",
            "can you do this for me": "YOU DO THIS ME",
            "stop":                   "STOP",
            "help":                   "HELP",
            "help me":                "HELP ME",
            "nice to meet you":       "MEET YOU NICE",
        }

        self.question_words = {"WHAT", "WHERE", "HOW", "WHEN", "WHY", "WHO"}
        self.time_words = {
            "TODAY", "TOMORROW", "YESTERDAY", "NOW",
            "MORNING", "EVENING", "NIGHT", "LATER",
            "BEFORE", "AFTER",
        }

    def map_token(self, word: str) -> str:
        if word in self.pronouns: return self.pronouns[word]
        if word in self.verb_map: return self.verb_map[word]
        return word.upper()

    def reorder_isl(self, words: List[str]) -> List[str]:
        time_tokens     = [w for w in words if w in self.time_words]
        question_tokens = [w for w in words if w in self.question_words]
        other_tokens    = [w for w in words if w not in self.time_words
                                            and w not in self.question_words]
        return time_tokens + other_tokens + question_tokens

    def nlp_reorder(self, sentence: str) -> str:
        words  = word_tokenize(sentence.lower())
        tagged = pos_tag(words)
        time_raw = {"today", "tomorrow", "yesterday", "now",
                    "morning", "evening", "night", "later"}

        subject, time, objects, verbs, question, other = [], [], [], [], [], []

        for word, tag in tagged:
            if word in self.stopwords: continue
            mapped = self.map_token(word)
            if mapped in self.question_words:                 question.append(mapped)
            elif word in self.pronouns:                       subject.append(mapped)
            elif word in time_raw:                            time.append(mapped)
            elif tag.startswith("V"):                         verbs.append(self.verb_map.get(word, word.upper()))
            elif tag.startswith("N") or tag.startswith("J"): objects.append(word.upper())
            elif tag in ("RB", "RBR", "RBS"):                other.append(word.upper())
            else:                                             other.append(mapped)

        gloss = time + subject + objects + verbs + other + question
        return " ".join(gloss) if gloss else sentence.upper()

    def translate(self, sentence: str, text_info=None) -> str:
        sentence       = sentence.lower().strip()
        is_question    = text_info.get("is_question", False)    if text_info else False
        is_exclamation = text_info.get("is_exclamation", False) if text_info else False

        if sentence in self.special_rules:
            return self._apply_marker(self.special_rules[sentence],
                                      is_question, is_exclamation)

        tokens = word_tokenize(sentence)
        tokens = [w for w in tokens if w.isalpha()]
        mapped = [self.map_token(w) for w in tokens if w not in self.stopwords]

        if not mapped:
            return ""

        reordered = self.reorder_isl(mapped)
        gloss = " ".join(reordered)
        return self._apply_marker(gloss, is_question, is_exclamation)

    def _apply_marker(self, gloss: str,
                      is_question: bool, is_exclamation: bool) -> str:
        if is_question and "QUESTION" not in gloss:
            words   = gloss.split()
            q_words = [w for w in words if w in self.question_words]
            other   = [w for w in words if w not in self.question_words]
            return " ".join(other + q_words) + " QUESTION"
        if is_exclamation:
            return gloss + " EXCLAMATION"
        return gloss


# ── AGENT 3: Sequence Resolver ────────────────────────────────────────────────
class SequenceResolver:

    # Kept as fallback when BiLSTM confidence < 0.85
    COMPOUND_RULES = [
        # trigrams
        (["HOW",   "ARE",  "YOU"],  "HOWAREYOU"),
        (["MY",    "NAME", "IS"],   "MYNAMEIS"),
        (["I",     "LOVE", "YOU"],  "ILOVEYOU"),
        # bigrams
        (["HOW",   "YOU"],          "HOWAREYOU"),
        (["THANK", "YOU"],          "THANKYOU"),
        (["ME",    "NAME"],         "MYNAMEIS"),
        (["GOOD",  "MORNING"],      "GOODMORNING"),
        (["GOOD",  "NIGHT"],        "GOODNIGHT"),
        (["GOOD",  "AFTERNOON"],    "GOODAFTERNOON"),
        (["ME",    "SORRY"],        "SORRY"),
    ]

    TOKEN_ALIASES = {
        "HI":  "HELLO",
        "HEY": "HELLO",
    }

    def _rule_based_resolve(self, tokens: List[str]) -> List[str]:
        """Original sliding window rule-based resolver — used as fallback."""
        result = []
        i = 0
        while i < len(tokens):
            matched = False
            for pattern, compound in self.COMPOUND_RULES:
                n      = len(pattern)
                window = tokens[i:i + n]
                if window == pattern:
                    result.append(compound)
                    i += n
                    matched = True
                    break
            if not matched:
                tok = tokens[i]
                result.append(self.TOKEN_ALIASES.get(tok, tok))
                i += 1
        return result

    def resolve(self, tokens: List[str]) -> List[str]:
        """
        Primary resolver — uses BiLSTM if available and confident.
        Falls back to rule-based sliding window if:
          - BiLSTM model not trained yet (bilstm_compound.pt missing)
          - BiLSTM confidence < 0.85
        """
        # Apply token aliases first
        tokens = [self.TOKEN_ALIASES.get(t, t) for t in tokens]

        try:
            from BiLSTM import resolve_compounds
            resolved, source = resolve_compounds(
                tokens, fallback_fn=self._rule_based_resolve
            )
            print(f"[SequenceResolver] source={source} resolved={resolved}")
            return resolved
        except ImportError:
            print("[SequenceResolver] bilstm_compound not available — using rules")
            return self._rule_based_resolve(tokens)
        except Exception as e:
            print(f"[SequenceResolver] BiLSTM error: {e} — using rules")
            return self._rule_based_resolve(tokens)


# ── ORCHESTRATOR ──────────────────────────────────────────────────────────────
class ISignOrchestrator:
    def __init__(self):
        self.text_agent  = TextUnderstandAgent()
        self.gloss_agent = GlossTranslator()
        self.resolver    = SequenceResolver()

    def run(self, text: str) -> str:
        print("\n[Agent 1] Understanding Text...")
        text_info = self.text_agent.process(text)
        print(f"  Intent:      {text_info['intent']}")
        print(f"  Question:    {text_info['is_question']}")
        print(f"  Exclamation: {text_info['is_exclamation']}")

        print("\n[Agent 2] Translating to ISL Gloss...")
        gloss      = self.gloss_agent.translate(text_info["clean_text"], text_info=text_info)
        marker_set = {"QUESTION", "EXCLAMATION"}
        raw_tokens = [t for t in gloss.split() if t not in marker_set]
        print(f"  Raw tokens:  {raw_tokens}")

        print("\n[Agent 3] Resolving compound signs...")
        resolved = self.resolver.resolve(raw_tokens)
        print(f"  Resolved:    {resolved}")

        markers     = [t for t in gloss.split() if t in marker_set]
        final_gloss = " ".join(resolved + markers)
        print(f"\nFinal ISL Gloss Output: {final_gloss}")
        return final_gloss

    def get_sequence(self, text: str):
        """
        Structured output consumed by app.py's run_hybrid() and agent.py.

        Returns
        -------
        final_gloss : str
            Space-separated gloss string including QUESTION/EXCLAMATION markers.
        resolved : list[str]
            Compound-resolved sign tokens (markers stripped by caller).
        text_info : dict
            Intent, is_question, is_exclamation, clean_text, etc.
        """
        text_info  = self.text_agent.process(text)
        gloss      = self.gloss_agent.translate(text_info["clean_text"], text_info=text_info)
        marker_set = {"QUESTION", "EXCLAMATION"}
        raw_tokens = [t for t in gloss.split() if t not in marker_set]
        resolved   = self.resolver.resolve(raw_tokens)
        markers    = [t for t in gloss.split() if t in marker_set]
        final_gloss = " ".join(resolved + markers)
        return final_gloss, resolved, text_info


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    system = ISignOrchestrator()

    test_sentences = [
        "hello", "hi", "namaste",
        "how are you?",
        "thank you", "thanks",
        "my name is Riya",
        "what is your name?",
        "sorry", "i am sorry",
        "i am fine", "i am deaf", "i love you",
        "who are you?", "where are you going?",
        "where have you been?", "how old are you?",
        "help me!", "stop!",
        "she is going", "he wants food",
        "I am going to school",
        "she wants to eat food",
        "can you do this for me",
        "time",
        "what is the time?",
    ]

    print("=" * 55)
    print("  ISL Gloss System — Full Pipeline Test")
    print("=" * 55)
    for s in test_sentences:
        system.run(s)
        print("-" * 55)

    print("\n" + "=" * 55)
    print("  Interactive Mode")
    print("=" * 55)
    while True:
        user_input = input("\nEnter English Sentence (or 'exit'): ")
        if user_input.lower() == "exit":
            break
        system.run(user_input)