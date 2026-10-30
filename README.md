# Sign Language Communication Platform (Agentic AI)

Type an English sentence and watch a 3D avatar sign it. A locally hosted LLM turns the sentence into sign-language gloss, a small BiLSTM model handles compound signs, and a React + Three.js frontend plays the animations.

## What it does

- Converts English text into a sequence of sign-language gloss words.
- Plays each sign on a 3D avatar: whole-word signs where one exists, and A to Z fingerspelling for everything else.
- Remembers each session and learns from thumbs up / thumbs down feedback, so a gloss that was marked bad is not repeated.

## How it works

```
English sentence
      |
      v
  Flask API (/translate)
      |
      v
  Ollama LLM agent  --tools-->  sign lookup, synonym map, fingerspelling check,
      |                          spaCy NER (names and places), rule-based gloss, domain detection
      v
  BiLSTM tagger (PyTorch)  -->  detects and merges compound signs
      |                          (falls back to rules if confidence < 0.85)
      v
  Gloss sequence  -->  React + Three.js avatar plays the signs
```

- **Agent (`backend/agent.py`):** an Ollama-first agent. The LLM calls tools to check whether a sign exists, find a synonym, fingerspell, detect names with spaCy, and get a rule-based suggestion. If Ollama is not reachable, the app falls back to the rule-based pipeline in `gloss.py`.
- **Compound signs (`backend/BiLSTM.py`):** a BiLSTM sequence tagger trained with BIO tags on training data generated from the project's compound-sign map. A prediction is used only when its confidence is at least 0.85; otherwise the rules decide.
- **Memory (`backend/storage.py`):** SQLite tables for sessions, feedback and corrections.
- **Frontend (`src/`):** React app with a Three.js avatar (`src/Model/model.glb`) and one animation file per sign.

## Sign coverage

| Type | Count |
|---|---|
| Whole-word signs | 10 (PLEASE, FOOD, ME, REST, NAMASTE, HOME, YOU, WATER, TIME, NAME) |
| Fingerspelling | A to Z |
| Synonym map | 118 English words routed to a sign or to fingerspelling |

Any word without a sign is fingerspelled. To add a sign, drop a new `.js` file in `src/Words/` or `src/Alphabets/` and call the reload endpoint (below).

## Tech stack

Python, Flask, Ollama (local LLM), PyTorch, spaCy, NLTK, SQLite, React, Three.js

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/translate` | POST | English text to gloss and sign sequence |
| `/feedback` | POST | Save a thumbs up / down rating |
| `/session/<session_id>` | GET, DELETE | Read or clear a session's memory |
| `/agent/config` | GET, POST | Read or change the agent settings (model, URL, max steps, temperature) |
| `/signs` | GET | List the available signs |
| `/signs/reload` | POST | Re-scan the sign files after adding new ones |
| `/health` | GET | Check that the backend is running |

## How to run

to run the LLM model first use in powershell: ollama serve

open 2 different terminals for each of the commands

to run the backend run: (first enter the backend folder by doing cd backend) python app.py

to run the website/frontend: (first go into the Signlanguage folder by cd signlanguage) npm start

## Project layout

```
backend/    Flask API, Ollama agent, BiLSTM model and vocab, gloss rules, SQLite storage
src/        React frontend: pages, avatar model, Words/ and Alphabets/ sign animations
public/     static files
```

## Limitations

- Only 10 words have whole-word animations. All other words are fingerspelled.
- The BiLSTM is trained on generated examples, so it covers the compound signs in the project's map and not free-form language.
- The LLM runs locally through Ollama, so translation quality and speed depend on the model and your machine.

## Author

Vedant Sawant: [LinkedIn](https://www.linkedin.com/in/vdnt-swnt/) · [GitHub](https://github.com/vdntswnt)
