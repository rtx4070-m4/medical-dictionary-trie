"""
benchmark.py - Performance Benchmarking Script

Measures:
  - Bulk insert speed (50,000 terms)
  - Exact search latency
  - Prefix autocomplete latency
  - Fuzzy search latency
  - Memory footprint

Run with:
    python benchmark.py

Author: Medical Dictionary Trie Project
License: MIT
"""

from __future__ import annotations
import sys
import time
import random
import string
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.dictionary import MedicalDictionary
from src.utils import benchmark, print_benchmark_report


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def generate_synthetic_terms(n: int) -> list[str]:
    """Generate n synthetic medical-sounding terms for stress testing."""
    prefixes = [
        "acute", "chronic", "benign", "malignant", "primary", "secondary",
        "idiopathic", "congenital", "acquired", "hereditary", "autoimmune",
        "inflammatory", "degenerative", "infectious", "neoplastic", "metabolic",
    ]
    roots = [
        "cardio", "hepato", "nephro", "neuro", "gastro", "pulmo", "dermato",
        "osteo", "hemo", "lympho", "thyro", "adeno", "myo", "arthro", "cyto",
    ]
    suffixes = [
        "pathy", "itis", "osis", "emia", "oma", "logy", "graphy", "plasty",
        "ectomy", "scopy", "tomy", "genesis", "megaly", "algia", "rrhea",
    ]

    terms = set()
    rng = random.Random(42)
    while len(terms) < n:
        parts = rng.choice(prefixes), rng.choice(roots), rng.choice(suffixes)
        terms.add(" ".join(parts))
    return list(terms)


def separator(title: str = "") -> None:
    width = 60
    if title:
        pad = (width - len(title) - 4) // 2
        print(f"\n{'═' * pad}  {title}  {'═' * pad}")
    else:
        print("═" * width)


# ─────────────────────────────────────────────────────────────
# Benchmark Suite
# ─────────────────────────────────────────────────────────────

def run_benchmarks() -> None:
    separator("Medical Dictionary Trie — Benchmark")
    print("  Generating 50,000 synthetic medical terms...")

    N = 50_000
    terms = generate_synthetic_terms(N)
    print(f"  ✓ Generated {len(terms):,} unique terms\n")

    # ── 1. Bulk Insert ────────────────────────────────────────
    separator("1. Bulk Insert")
    d = MedicalDictionary()
    t0 = time.perf_counter()
    inserted = d.load_from_list(terms)
    elapsed_insert = (time.perf_counter() - t0) * 1000

    print(f"  Terms inserted : {inserted:,}")
    print(f"  Trie nodes     : {d.node_count:,}")
    print(f"  Total time     : {elapsed_insert:.1f} ms")
    print(f"  Per term       : {elapsed_insert / inserted * 1000:.2f} µs")
    stats = d.stats()
    print(f"  Memory est.    : {stats['memory_estimate_kb']:.1f} KB")

    # Pick some sample terms for search tests
    sample_exact  = random.Random(1).sample(terms, 100)
    sample_prefix = [t[:max(3, random.Random(2).randint(3, 6))] for t in sample_exact]

    # ── 2. Exact Search ───────────────────────────────────────
    separator("2. Exact Search")
    it = iter(sample_exact)
    s = benchmark(lambda: d.search(next(it) if True else "x"), iterations=100)
    # Re-run properly
    times = []
    for term in sample_exact:
        t0 = time.perf_counter()
        d.search(term)
        times.append((time.perf_counter() - t0) * 1e6)
    avg_us = sum(times) / len(times)
    print(f"  Iterations : 100")
    print(f"  Average    : {avg_us:.2f} µs/search")
    print(f"  Min        : {min(times):.2f} µs")
    print(f"  Max        : {max(times):.2f} µs")

    # ── 3. Prefix Autocomplete ───────────────────────────────
    separator("3. Prefix Autocomplete (top-10)")
    ac_times = []
    for pfx in sample_prefix:
        t0 = time.perf_counter()
        d.autocomplete(pfx, top_k=10)
        ac_times.append((time.perf_counter() - t0) * 1e6)

    print(f"  Iterations : {len(ac_times)}")
    print(f"  Average    : {sum(ac_times)/len(ac_times):.2f} µs/autocomplete")
    print(f"  Min        : {min(ac_times):.2f} µs")
    print(f"  Max        : {max(ac_times):.2f} µs")

    # ── 4. Fuzzy Search ──────────────────────────────────────
    separator("4. Fuzzy Search (max_distance=2)")
    # Introduce typos
    def typo(s: str) -> str:
        """Swap 1 character in the string."""
        if len(s) < 4:
            return s
        idx = random.Random(99).randint(1, len(s) - 2)
        return s[:idx] + random.choice(string.ascii_lowercase) + s[idx+1:]

    typo_queries = [typo(t) for t in sample_exact[:50]]
    fuzz_times = []
    for q in typo_queries:
        t0 = time.perf_counter()
        d.fuzzy_search(q, top_k=5, max_distance=2)
        fuzz_times.append((time.perf_counter() - t0) * 1000)

    print(f"  Iterations : {len(fuzz_times)}")
    print(f"  Average    : {sum(fuzz_times)/len(fuzz_times):.2f} ms/fuzzy_search")
    print(f"  Min        : {min(fuzz_times):.2f} ms")
    print(f"  Max        : {max(fuzz_times):.2f} ms")

    # ── 5. Real-world data file benchmark ────────────────────
    data_path = Path(__file__).parent / "data" / "sample_medical_terms.txt"
    if data_path.exists():
        separator("5. Real Data File")
        d2 = MedicalDictionary()
        t0 = time.perf_counter()
        n = d2.load_from_file(str(data_path))
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  Loaded {n} terms in {elapsed:.1f} ms from {data_path.name}")
        # Autocomplete on "dia"
        ac_times2 = []
        for _ in range(1000):
            t0 = time.perf_counter()
            d2.autocomplete("dia", top_k=10)
            ac_times2.append((time.perf_counter() - t0) * 1e6)
        print(f"  autocomplete('dia') × 1000: avg {sum(ac_times2)/len(ac_times2):.2f} µs")

    separator("Benchmark Complete")
    print()


if __name__ == "__main__":
    run_benchmarks()
