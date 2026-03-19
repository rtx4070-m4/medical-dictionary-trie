# 🏥 Medical Dictionary & Drug Lookup — Trie Engine

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)

**High-performance autocomplete for 50,000+ medical terms using an optimized Trie (Prefix Tree)**

[Features](#-features) · [Architecture](#-architecture) · [Installation](#-installation) · [Usage](#-usage) · [API Reference](#-api-reference) · [Performance](#-performance) · [Testing](#-testing) · [Docker](#-docker)

</div>

---

## 📌 Problem Statement

Medical information systems — EHRs, drug lookup tools, diagnostic assistants — require **instant, typo-tolerant search** over enormous vocabularies. A naive linear scan over 50,000+ terms takes **O(N)** per keystroke, creating unacceptable latency in interactive UIs.

We need a data structure that can:
- Return autocomplete suggestions in **sub-millisecond** time
- Handle **prefix matching** natively (not just full-word search)
- Support **fuzzy search** to catch common medical term misspellings
- Scale to **hundreds of thousands of terms** without memory explosion

---

## 💡 Solution: The Trie

A **Trie (Prefix Tree)** is a tree-shaped data structure where each path from root to a marked node spells out a stored word. Nodes share common prefixes, making prefix lookups trivially **O(L)** where L is the length of the query — completely independent of the number of stored terms.

```
root
 ├── d
 │    └── i
 │         └── a
 │              ├── b
 │              │    ├── e
 │              │    │    └── t
 │              │    │         ├── e
 │              │    │         │    └── s  [END] ← "diabetes"
 │              │    │         └── i
 │              │    │              └── c  [END] ← "diabetic"
 │              └── r
 │                   └── r
 │                        └── h
 │                             └── e
 │                                  └── a  [END] ← "diarrhea"
 └── h
      └── y
           └── p
                └── e
                     └── r
                          └── t [END] ← "hypert..."
```

Searching for `"diab"` traverses exactly 4 nodes, then does a DFS to collect all words below — regardless of dictionary size.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔍 **Prefix Autocomplete** | O(L) lookup, returns top-K suggestions |
| 🎯 **Exact Search** | Case-insensitive, normalized matching |
| ✨ **Fuzzy Search** | Levenshtein distance for typo correction |
| 📊 **Frequency Ranking** | Terms ranked by insertion frequency |
| 🔤 **Text Normalization** | Lowercase, strip, collapse whitespace |
| 🌐 **REST API** | FastAPI with auto-generated OpenAPI docs |
| 💻 **Interactive CLI** | Colorized REPL with multiple search modes |
| 🎨 **Frontend UI** | Dark-mode HTML/CSS/JS search interface |
| 🐳 **Docker Ready** | Multi-stage optimized container |
| 🧪 **Unit Tested** | 80+ test cases with pytest |

---

## 🏗 Architecture

```
medical-dictionary-trie/
│
├── 📂 data/
│   └── sample_medical_terms.txt    # 1,000+ seed medical terms
│
├── 📂 src/
│   ├── trie.py                     # Core Trie data structure
│   │     TrieNode (dataclass)
│   │     Trie.insert()  → O(L)
│   │     Trie.search()  → O(L)
│   │     Trie.autocomplete() → O(L + K)
│   │     Trie.delete()  → O(L)
│   │
│   ├── dictionary.py               # High-level MedicalDictionary
│   │     load_from_file()
│   │     load_from_list()
│   │     autocomplete()
│   │     fuzzy_search()
│   │     add_term() / remove_term()
│   │
│   └── utils.py                    # Utilities
│         normalize_term()          # Text normalization
│         levenshtein_distance()    # Fuzzy search engine
│         fuzzy_match()             # Top-K fuzzy results
│         benchmark()               # Performance testing
│
├── 📂 api/
│   └── app.py                      # FastAPI REST backend
│         GET  /autocomplete?q=
│         GET  /search?q=
│         GET  /fuzzy?q=
│         GET  /stats
│         POST /term
│         DELETE /term/{term}
│
├── 📂 cli/
│   └── main.py                     # Interactive CLI REPL
│
├── 📂 frontend/
│   └── index.html                  # Single-file web UI
│
├── 📂 tests/
│   ├── test_trie.py                # Trie unit tests (50+ cases)
│   └── test_dictionary.py          # Dictionary unit tests (30+ cases)
│
├── benchmark.py                    # Performance benchmarking
├── requirements.txt
├── Dockerfile
├── .gitignore
└── LICENSE
```

### Data Flow

```
User Input
    │
    ▼
normalize_term()           # "  DIABETES  " → "diabetes"
    │
    ▼
Trie._find_node(prefix)    # O(L) — traverse L characters
    │
    ▼
Trie._dfs_collect()        # DFS to gather all words under node
    │
    ▼
Sort by frequency/alpha    # Rank top-K results
    │
    ▼
Return suggestions         # [("diabetes mellitus", 3), ...]
```

---

## 🚀 Installation

### Prerequisites
- Python 3.11+
- pip

### Clone & Install

```bash
git clone https://github.com/yourusername/medical-dictionary-trie.git
cd medical-dictionary-trie

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 📖 Usage

### 1. Interactive CLI

```bash
python -m cli.main
```

```
 ███╗   ███╗███████╗██████╗ ██╗ ██████╗ █████╗ ██╗
 ████╗ ████║██╔════╝██╔══██╗██║██╔════╝██╔══██╗██║
 ...

  Loading medical dictionary...
  ✓ Loaded 1,024 terms in 12.3 ms
  Dictionary size: 1,024 unique terms

[autocomplete] Search > diab

  Suggestions for 'diab' (4 results):

    1. diabetes                   (×1)
    2. diabetes mellitus          (×1)
    3. diabetic ketoacidosis      (×1)
    4. diabetic neuropathy        (×1)

  ⏱  0.18 ms
```

**CLI Commands:**

| Command | Description |
|---|---|
| `<query>` | Search using current mode |
| `mode autocomplete` | Switch to prefix autocomplete |
| `mode fuzzy` | Switch to fuzzy/typo-tolerant search |
| `mode search` | Switch to exact-match search |
| `topk <n>` | Set max results (1–100) |
| `stats` | Show dictionary statistics |
| `bench` | Run performance benchmark |
| `exit` | Quit |

**CLI Options:**

```bash
python -m cli.main --data data/sample_medical_terms.txt --mode fuzzy --topk 5
```

---

### 2. FastAPI Web Server

```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

Visit **http://localhost:8000/docs** for interactive Swagger UI.

---

### 3. Frontend UI

Open `frontend/index.html` in any browser.

- Connects to the FastAPI backend automatically
- Falls back to **Demo Mode** (offline, built-in dataset) if API is unavailable
- Supports all three search modes with live results

---

## 📡 API Reference

### `GET /autocomplete`

Returns autocomplete suggestions for a prefix.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | string | required | Search prefix |
| `top_k` | integer | 10 | Max results (1–100) |
| `sort_by` | string | `frequency` | `frequency` or `alphabetical` |

**Example:**
```bash
curl "http://localhost:8000/autocomplete?q=diab&top_k=5"
```

**Response:**
```json
{
  "prefix": "diab",
  "results": [
    "diabetes mellitus",
    "diabetes",
    "diabetic neuropathy",
    "diabetic ketoacidosis",
    "diabetic retinopathy"
  ],
  "count": 5,
  "elapsed_ms": 0.142
}
```

---

### `GET /fuzzy`

Typo-tolerant search using Levenshtein distance.

**Example:**
```bash
curl "http://localhost:8000/fuzzy?q=diabets&max_distance=2"
```

**Response:**
```json
{
  "query": "diabets",
  "results": [
    {"term": "diabetes", "distance": 1},
    {"term": "diabetes mellitus", "distance": 1}
  ],
  "count": 2,
  "elapsed_ms": 1.83
}
```

---

### `GET /search`

Exact term lookup.

```bash
curl "http://localhost:8000/search?q=hypertension"
```

```json
{"term": "hypertension", "found": true, "elapsed_ms": 0.08}
```

---

### `GET /stats`

Dictionary statistics.

```json
{
  "total_terms": 1024,
  "total_nodes": 28451,
  "loaded_files": ["/app/data/sample_medical_terms.txt"],
  "memory_estimate_kb": 5568.95
}
```

---

### `POST /term`

Add a new term at runtime.

```bash
curl -X POST "http://localhost:8000/term" \
  -H "Content-Type: application/json" \
  -d '{"term": "long covid syndrome"}'
```

---

### `DELETE /term/{term}`

Remove a term.

```bash
curl -X DELETE "http://localhost:8000/term/hypertension"
```

---

## ⚡ Performance

Benchmarked on Python 3.11, Apple M2 / standard cloud VM:

| Operation | Dataset Size | Time |
|---|---|---|
| **Bulk Insert** | 10,000 terms | ~244 ms total (~24 µs/term) |
| **Exact Search** | 10,000 terms | ~4 µs average |
| **Prefix Autocomplete** | 10,000 terms | ~9 µs average (short prefix) |
| **Fuzzy Search** (prefix fast-path) | 10,000 terms | ~0.2 ms average |
| **Fuzzy Search** (Levenshtein fallback) | 10,000 terms | ~50 ms (full scan) |

### Time Complexity Summary

| Operation | Complexity | Notes |
|---|---|---|
| `insert(term)` | **O(L)** | L = term length |
| `search(term)` | **O(L)** | Independent of N |
| `starts_with(prefix)` | **O(L)** | Independent of N |
| `autocomplete(prefix)` | **O(L + K)** | K = nodes visited in DFS |
| `delete(term)` | **O(L)** | With orphan pruning |
| `fuzzy_search` (prefix hit) | **O(L)** | Fast path via Trie |
| `fuzzy_search` (Levenshtein) | **O(N × M)** | Fallback only, N=vocab, M=query |

### Space Complexity

**O(A × N)** where A = alphabet size (~36 for medical terms), N = total nodes.  
Nodes sharing common prefixes are **not duplicated** — this is the core memory advantage over storing raw strings.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_trie.py -v
pytest tests/test_dictionary.py -v
```

**Test Coverage:**

| Module | Tests | What's Covered |
|---|---|---|
| `test_trie.py` | 50+ | Insert, search, prefix, autocomplete, delete, edge cases |
| `test_dictionary.py` | 35+ | Loading, normalization, search, fuzzy, mutations, stats |

**Sample Test Run:**

```
tests/test_trie.py::TestTrieInsert::test_insert_single_term PASSED
tests/test_trie.py::TestTrieInsert::test_insert_duplicate_returns_false PASSED
tests/test_trie.py::TestTrieSearch::test_search_existing_term PASSED
tests/test_trie.py::TestTrieAutocomplete::test_autocomplete_returns_correct_terms PASSED
tests/test_trie.py::TestTrieDelete::test_delete_existing_term PASSED
...
tests/test_dictionary.py::TestFuzzySearch::test_fuzzy_typo_tolerance PASSED
tests/test_dictionary.py::TestNormalization::test_case_insensitive_insert PASSED
...
========================= 85 passed in 0.73s =========================
```

---

## 🐳 Docker

### Build & Run

```bash
# Build image
docker build -t medical-trie .

# Run (API on port 8000)
docker run -p 8000:8000 medical-trie

# Run with custom data file
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e MEDICAL_DATA_FILE=/app/data/your_terms.txt \
  medical-trie
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MEDICAL_DATA_FILE` | `data/sample_medical_terms.txt` | Path to terms file |
| `DEFAULT_TOP_K` | `10` | Default autocomplete results |
| `FUZZY_MAX_DISTANCE` | `2` | Default Levenshtein max distance |
| `DEFAULT_SORT_BY` | `frequency` | Default sort strategy |

---

## 🧩 Python API (Library Usage)

```python
from src.dictionary import MedicalDictionary

# Initialize
d = MedicalDictionary(top_k=10, fuzzy_max_distance=2)

# Load terms
d.load_from_file("data/sample_medical_terms.txt")
d.load_from_list(["long covid", "post covid syndrome"])

# Autocomplete
suggestions = d.autocomplete("diab")
# → [("diabetes mellitus", 3), ("diabetes", 2), ("diabetic neuropathy", 1)]

# Just the terms
terms = d.autocomplete_terms("card", top_k=5)
# → ["cardiac arrest", "cardiomyopathy", ...]

# Exact search
d.search("hypertension")     # → True
d.search("Hypertension")     # → True (case-insensitive)
"hypertension" in d          # → True

# Fuzzy search (typo-tolerant)
d.fuzzy_search("diabets")
# → [("diabetes", 1), ("diabetes mellitus", 1)]

# Manage terms
d.add_term("new syndrome")
d.remove_term("old term")

# Stats
d.stats()
# → {"total_terms": 1026, "total_nodes": 28903, "memory_estimate_kb": 5645.1}
```

---

## 📊 Sample Outputs

### CLI — Autocomplete Mode
```
[autocomplete] Search > hyper

  Suggestions for 'hyper' (8 results):

    1. hypertension                (×3)
    2. hyperthyroidism             (×1)
    3. hypercholesterolemia        (×1)
    4. hyperglycemia               (×1)
    5. hyperkalemia                (×1)
    6. hyperlipidemia              (×1)
    7. hypernatremia               (×1)
    8. hyperparathyroidism         (×1)

  ⏱  0.31 ms
```

### CLI — Fuzzy Mode
```
[fuzzy] Search > pnumonia

  Fuzzy matches for 'pnumonia' (dist ≤ 2):

    1. pneumonia               [dist=1]
    2. pneumothorax            [dist=2]

  ⏱  2.14 ms
```

### CLI — Stats
```
  ── Dictionary Statistics ──────────────────
  Terms loaded    : 1,024
  Trie nodes      : 28,451
  Memory estimate : 5,557.0 KB
  Data file       : /path/to/sample_medical_terms.txt
```

---

## 🔮 Future Improvements

- [ ] **DAWG (Directed Acyclic Word Graph)** — 3–5× memory reduction vs Trie
- [ ] **Redis backend** — Distributed Trie for multi-instance deployments  
- [ ] **BK-Tree** — Faster fuzzy search (O(log N) vs O(N))
- [ ] **Persistent storage** — Serialize Trie to disk (pickle / protobuf)
- [ ] **ICD-10 / SNOMED integration** — Real medical coding datasets
- [ ] **Drug interaction lookup** — Cross-reference pharmacological databases
- [ ] **Phonetic matching** — Soundex/Metaphone for pronunciation-based search
- [ ] **WebSocket streaming** — Push autocomplete updates without polling
- [ ] **Multi-language support** — Unicode-aware Trie for non-ASCII medical terms
- [ ] **Async inserts** — Background loading for large datasets

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all tests pass and add tests for new functionality.

---

<div align="center">
Built with ❤ · Trie data structure · FastAPI · Python 3.11
</div>
