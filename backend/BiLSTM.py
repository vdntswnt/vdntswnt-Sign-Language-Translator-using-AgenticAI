from __future__ import annotations
import os
import json
import argparse
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# ── Paths ─────────────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bilstm_compound.pt")
VOCAB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bilstm_vocab.json")

# ── Vocabulary ────────────────────────────────────────────────────────────────
VOCAB = [
    "<PAD>", "<UNK>",
    # Sign file tokens
    "DEAF", "HE", "HELLO", "HOME", "NAMASTE", "SHE", "SORRY", "THANKYOU",
    "TIME", "YOU", "ME", "MY", "YOUR", "HIS", "HER",
    # Compound parts
    "THANK", "GOOD", "MORNING", "NIGHT", "AFTERNOON", "HOW", "ARE",
    "NAME", "IS", "I", "LOVE", "MYNAMEIS", "HOWAREYOU", "GOODMORNING",
    "GOODNIGHT", "GOODAFTERNOON", "ILOVEYOU",
    # Common gloss tokens
    "STOP", "HELP", "GO", "EAT", "KNOW", "WANT", "NEED", "COME",
    "SAY", "SAID", "LIVE", "WORK", "STUDY", "PLAY", "FEEL", "THINK",
    "FOOD", "WATER", "SCHOOL", "WHAT", "WHERE", "WHO", "WHY", "WHEN",
    "TODAY", "TOMORROW", "YESTERDAY", "NOW", "HERE", "THERE",
    "YES", "NO", "NOT", "MORE", "LESS", "BIG", "SMALL",
]

TOKEN2IDX = {t: i for i, t in enumerate(VOCAB)}
TAG2IDX   = {"O": 0, "B-COMP": 1, "I-COMP": 2}
IDX2TAG   = {v: k for k, v in TAG2IDX.items()}

# ── Compound map (token sequence → merged token) ──────────────────────────────
# Used at inference time to know what to merge B+I into
COMPOUND_MAP = {
    ("THANK",  "YOU"):           "THANKYOU",
    ("GOOD",   "MORNING"):       "GOODMORNING",
    ("GOOD",   "NIGHT"):         "GOODNIGHT",
    ("GOOD",   "AFTERNOON"):     "GOODAFTERNOON",
    ("HOW",    "YOU"):           "HOWAREYOU",
    ("HOW",    "ARE",  "YOU"):   "HOWAREYOU",
    ("MY",     "NAME", "IS"):    "MYNAMEIS",
    ("ME",     "NAME"):          "MYNAMEIS",
    ("I",      "LOVE", "YOU"):   "ILOVEYOU",
    ("ME",     "SORRY"):         "SORRY",
}

# ── Training data ─────────────────────────────────────────────────────────────
# Format: ([tokens], [BIO tags])
# Generated from COMPOUND_MAP + negative examples

def generate_training_data() -> list[tuple[list[str], list[str]]]:
    data = []

    # ── Positive examples from each compound ─────────────────────────────────
    compound_contexts = [
        # THANKYOU
        (["THANK", "YOU"],                    ["B-COMP", "I-COMP"]),
        (["HE", "THANK", "YOU"],              ["O", "B-COMP", "I-COMP"]),
        (["THANK", "YOU", "HE"],              ["B-COMP", "I-COMP", "O"]),
        (["ME", "THANK", "YOU"],              ["O", "B-COMP", "I-COMP"]),
        (["THANK", "YOU", "ME"],              ["B-COMP", "I-COMP", "O"]),
        (["SHE", "THANK", "YOU", "HE"],       ["O", "B-COMP", "I-COMP", "O"]),
        (["THANK", "YOU", "TIME"],            ["B-COMP", "I-COMP", "O"]),
        (["HELLO", "THANK", "YOU"],           ["O", "B-COMP", "I-COMP"]),

        # GOODMORNING
        (["GOOD", "MORNING"],                 ["B-COMP", "I-COMP"]),
        (["HE", "GOOD", "MORNING"],           ["O", "B-COMP", "I-COMP"]),
        (["GOOD", "MORNING", "YOU"],          ["B-COMP", "I-COMP", "O"]),
        (["ME", "GOOD", "MORNING"],           ["O", "B-COMP", "I-COMP"]),
        (["GOOD", "MORNING", "HE"],           ["B-COMP", "I-COMP", "O"]),
        (["SHE", "GOOD", "MORNING", "ME"],    ["O", "B-COMP", "I-COMP", "O"]),
        (["HELLO", "GOOD", "MORNING"],        ["O", "B-COMP", "I-COMP"]),

        # GOODNIGHT
        (["GOOD", "NIGHT"],                   ["B-COMP", "I-COMP"]),
        (["HE", "GOOD", "NIGHT"],             ["O", "B-COMP", "I-COMP"]),
        (["GOOD", "NIGHT", "ME"],             ["B-COMP", "I-COMP", "O"]),
        (["ME", "GOOD", "NIGHT"],             ["O", "B-COMP", "I-COMP"]),

        # GOODAFTERNOON
        (["GOOD", "AFTERNOON"],               ["B-COMP", "I-COMP"]),
        (["HE", "GOOD", "AFTERNOON"],         ["O", "B-COMP", "I-COMP"]),
        (["GOOD", "AFTERNOON", "YOU"],        ["B-COMP", "I-COMP", "O"]),

        # HOWAREYOU
        (["HOW", "YOU"],                      ["B-COMP", "I-COMP"]),
        (["ME", "HOW", "YOU"],                ["O", "B-COMP", "I-COMP"]),
        (["HOW", "YOU", "HE"],                ["B-COMP", "I-COMP", "O"]),
        (["HELLO", "HOW", "YOU"],             ["O", "B-COMP", "I-COMP"]),
        (["HOW", "ARE", "YOU"],               ["B-COMP", "I-COMP", "I-COMP"]),
        (["HE", "HOW", "ARE", "YOU"],         ["O", "B-COMP", "I-COMP", "I-COMP"]),

        # MYNAMEIS
        (["ME", "NAME"],                      ["B-COMP", "I-COMP"]),
        (["MY", "NAME", "IS"],                ["B-COMP", "I-COMP", "I-COMP"]),
        (["HELLO", "ME", "NAME"],             ["O", "B-COMP", "I-COMP"]),
        (["ME", "NAME", "HE"],                ["B-COMP", "I-COMP", "O"]),
        (["MY", "NAME", "IS", "YOU"],         ["B-COMP", "I-COMP", "I-COMP", "O"]),

        # ILOVEYOU
        (["I", "LOVE", "YOU"],                ["B-COMP", "I-COMP", "I-COMP"]),
        (["ME", "I", "LOVE", "YOU"],          ["O", "B-COMP", "I-COMP", "I-COMP"]),
        (["I", "LOVE", "YOU", "HE"],          ["B-COMP", "I-COMP", "I-COMP", "O"]),
        (["SHE", "I", "LOVE", "YOU"],         ["O", "B-COMP", "I-COMP", "I-COMP"]),

        # SORRY (from ME SORRY)
        (["ME", "SORRY"],                     ["B-COMP", "I-COMP"]),
        (["HE", "ME", "SORRY"],               ["O", "B-COMP", "I-COMP"]),
        (["ME", "SORRY", "YOU"],              ["B-COMP", "I-COMP", "O"]),
        (["SHE", "ME", "SORRY", "HE"],        ["O", "B-COMP", "I-COMP", "O"]),
    ]
    data.extend(compound_contexts)

    # ── Negative examples (no compound) ───────────────────────────────────────
    negatives = [
        (["HE", "HOME"],              ["O", "O"]),
        (["YOU", "SORRY"],            ["O", "O"]),
        (["ME", "HELLO"],             ["O", "O"]),
        (["SHE", "DEAF"],             ["O", "O"]),
        (["TIME", "YOU"],             ["O", "O"]),
        (["HE", "SHE", "HOME"],       ["O", "O", "O"]),
        (["YOU", "GO", "WHERE"],      ["O", "O", "O"]),
        (["ME", "EAT", "FOOD"],       ["O", "O", "O"]),
        (["HELLO", "YOU"],            ["O", "O"]),
        (["HE", "DEAF"],              ["O", "O"]),
        (["YOU", "HOME", "WHERE"],    ["O", "O", "O"]),
        (["ME", "KNOW", "NOT"],       ["O", "O", "O"]),
        (["SHE", "GO"],               ["O", "O"]),
        (["TIME", "WHAT"],            ["O", "O"]),
        (["YOU", "WHO"],              ["O", "O"]),
        (["NAMASTE", "YOU"],          ["O", "O"]),
        (["HE", "COME", "WHERE"],     ["O", "O", "O"]),
        (["ME", "LIVE", "WHERE"],     ["O", "O", "O"]),
        (["YOU", "WORK", "WHERE"],    ["O", "O", "O"]),
        (["SHE", "FEEL", "HOW"],      ["O", "O", "O"]),
        (["HELLO"],                   ["O"]),
        (["YOU"],                     ["O"]),
        (["SORRY"],                   ["O"]),
        (["TIME"],                    ["O"]),
        (["HE", "WANT", "FOOD"],      ["O", "O", "O"]),
        (["ME", "SAY", "COME"],       ["O", "O", "O"]),
    ]
    data.extend(negatives)
    return data


# ── Dataset ───────────────────────────────────────────────────────────────────

class CompoundDataset(Dataset):
    def __init__(self, data: list):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        tokens, tags = self.data[idx]
        x = torch.tensor([TOKEN2IDX.get(t, TOKEN2IDX["<UNK>"]) for t in tokens])
        y = torch.tensor([TAG2IDX[t] for t in tags])
        return x, y


def collate(batch):
    xs, ys = zip(*batch)
    xs = nn.utils.rnn.pad_sequence(xs, batch_first=True, padding_value=0)
    ys = nn.utils.rnn.pad_sequence(ys, batch_first=True, padding_value=-1)
    return xs, ys


# ── Model ─────────────────────────────────────────────────────────────────────

class BiLSTMTagger(nn.Module):
    def __init__(self, vocab_size: int, embed_dim: int = 64,
                 hidden_dim: int = 128, num_tags: int = 3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.bilstm    = nn.LSTM(
            embed_dim, hidden_dim,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
            dropout=0.3,
        )
        self.dropout = nn.Dropout(0.3)
        self.linear  = nn.Linear(hidden_dim * 2, num_tags)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb        = self.dropout(self.embedding(x))
        out, _     = self.bilstm(emb)
        out        = self.dropout(out)
        logits     = self.linear(out)
        return logits

    def predict_with_confidence(self, tokens: list[str]) -> tuple[list[str], float]:
        """
        Returns (tag_list, min_confidence).
        min_confidence is used as the gate — if < 0.85 fall back to rules.
        """
        self.eval()
        with torch.no_grad():
            idxs   = [TOKEN2IDX.get(t, TOKEN2IDX["<UNK>"]) for t in tokens]
            x      = torch.tensor(idxs).unsqueeze(0)
            logits = self.forward(x).squeeze(0)
            probs  = torch.softmax(logits, dim=-1)
            conf, preds = probs.max(dim=-1)
            tags       = [IDX2TAG[p.item()] for p in preds]
            min_conf   = conf.min().item()
        return tags, min_conf


# ── Merge BIO tags → token list ───────────────────────────────────────────────

def merge_bio_tags(tokens: list[str], tags: list[str]) -> list[str]:
    """
    Merges tokens marked B-COMP/I-COMP into compound tokens.
    Uses COMPOUND_MAP to find the canonical compound name.
    Falls back to concatenation if not in map.
    """
    result  = []
    i       = 0
    while i < len(tokens):
        if tags[i] == "B-COMP":
            compound_tokens = [tokens[i]]
            j = i + 1
            while j < len(tokens) and tags[j] == "I-COMP":
                compound_tokens.append(tokens[j])
                j += 1
            # Look up canonical compound name
            key = tuple(compound_tokens)
            merged = COMPOUND_MAP.get(key, "".join(compound_tokens))
            result.append(merged)
            i = j
        else:
            result.append(tokens[i])
            i += 1
    return result


# ── Training ──────────────────────────────────────────────────────────────────

def train(epochs: int = 150, batch_size: int = 4, lr: float = 0.001):
    data    = generate_training_data()
    dataset = CompoundDataset(data)
    loader  = DataLoader(dataset, batch_size=batch_size,
                         shuffle=True, collate_fn=collate)

    model     = BiLSTMTagger(vocab_size=len(VOCAB))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=50, gamma=0.5)
    loss_fn   = nn.CrossEntropyLoss(ignore_index=-1)

    print(f"[BiLSTM] Training on {len(data)} examples for {epochs} epochs...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for x, y in loader:
            optimizer.zero_grad()
            logits = model(x)
            loss   = loss_fn(logits.view(-1, 3), y.view(-1))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        if (epoch + 1) % 25 == 0:
            print(f"  Epoch {epoch+1:3d} | loss {total_loss:.4f}")

    # Save model + vocab
    torch.save(model.state_dict(), MODEL_PATH)
    with open(VOCAB_PATH, "w") as f:
        json.dump({"token2idx": TOKEN2IDX, "tag2idx": TAG2IDX}, f)

    print(f"[BiLSTM] Saved model → {MODEL_PATH}")
    print(f"[BiLSTM] Saved vocab → {VOCAB_PATH}")
    return model


# ── Load pretrained model ─────────────────────────────────────────────────────

def load_model() -> BiLSTMTagger | None:
    """Load trained model from disk. Returns None if not trained yet."""
    if not os.path.exists(MODEL_PATH):
        print(f"[BiLSTM] No trained model found at {MODEL_PATH}")
        print(f"[BiLSTM] Run: python bilstm_compound.py")
        return None
    model = BiLSTMTagger(vocab_size=len(VOCAB))
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    print(f"[BiLSTM] Model loaded from {MODEL_PATH}")
    return model


# ── Main inference function (called by gloss.py) ──────────────────────────────

CONFIDENCE_GATE = 0.85   # use BiLSTM if conf >= this, else fall back to rules

_model: BiLSTMTagger | None = None

def resolve_compounds(tokens: list[str],
                       fallback_fn=None) -> tuple[list[str], str]:
    """
    Primary entry point for gloss.py SequenceResolver.

    Parameters
    ----------
    tokens      : list of uppercase gloss tokens
    fallback_fn : callable — the old rule-based resolve function
                  called when model confidence < CONFIDENCE_GATE

    Returns
    -------
    resolved : list of tokens with compounds merged
    source   : "bilstm" | "rules" (for logging/debugging)
    """
    global _model
    if _model is None:
        _model = load_model()

    # No model trained yet — use rules
    if _model is None:
        if fallback_fn:
            return fallback_fn(tokens), "rules"
        return tokens, "rules"

    tags, confidence = _model.predict_with_confidence(tokens)

    print(f"[BiLSTM] tokens={tokens} tags={tags} conf={confidence:.3f}")

    if confidence >= CONFIDENCE_GATE:
        resolved = merge_bio_tags(tokens, tags)
        print(f"[BiLSTM] resolved={resolved} (via BiLSTM)")
        return resolved, "bilstm"
    else:
        print(f"[BiLSTM] confidence {confidence:.3f} < {CONFIDENCE_GATE} → falling back to rules")
        if fallback_fn:
            return fallback_fn(tokens), "rules"
        return tokens, "rules"


# ── Test / demo ───────────────────────────────────────────────────────────────

def test_model(model: BiLSTMTagger):
    test_cases = [
        (["THANK", "YOU"],                  "THANKYOU"),
        (["HE", "THANK", "YOU"],            "HE THANKYOU"),
        (["GOOD", "MORNING"],               "GOODMORNING"),
        (["GOOD", "MORNING", "YOU"],        "GOODMORNING YOU"),
        (["HOW", "YOU"],                    "HOWAREYOU"),
        (["HOW", "ARE", "YOU"],             "HOWAREYOU"),
        (["ME", "NAME"],                    "MYNAMEIS"),
        (["MY", "NAME", "IS"],              "MYNAMEIS"),
        (["I", "LOVE", "YOU"],              "ILOVEYOU"),
        (["ME", "SORRY"],                   "SORRY"),
        (["GOOD", "NIGHT"],                 "GOODNIGHT"),
        (["HE", "HOME"],                    "HE HOME"),       # no compound
        (["YOU", "GO", "WHERE"],            "YOU GO WHERE"),  # no compound
        (["ME", "EAT", "FOOD"],             "ME EAT FOOD"),   # no compound
        (["HELLO", "THANK", "YOU", "HE"],   "HELLO THANKYOU HE"),
    ]

    print("\n[BiLSTM] Test results:")
    print(f"{'Input':<40} {'Expected':<25} {'Got':<25} {'Conf':>6} {'Pass'}")
    print("-" * 110)
    passed = 0
    for tokens, expected in test_cases:
        tags, conf = model.predict_with_confidence(tokens)
        got = " ".join(merge_bio_tags(tokens, tags))
        ok  = got == expected
        if ok: passed += 1
        print(f"{str(tokens):<40} {expected:<25} {got:<25} {conf:>6.3f} {'✓' if ok else '✗'}")
    print(f"\nPassed: {passed}/{len(test_cases)}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",   action="store_true", help="Run test predictions")
    parser.add_argument("--epochs", type=int, default=150)
    args = parser.parse_args()

    if args.test and os.path.exists(MODEL_PATH):
        model = load_model()
        test_model(model)
    else:
        model = train(epochs=args.epochs)
        test_model(model)