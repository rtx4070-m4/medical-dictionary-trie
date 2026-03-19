"""
main.py - Interactive CLI for Medical Dictionary Trie

Usage:
    python -m cli.main
    python -m cli.main --data path/to/terms.txt
    python -m cli.main --mode fuzzy

Modes:
    autocomplete  (default) - prefix search with suggestions
    fuzzy                   - typo-tolerant search
    search                  - exact match lookup

Author: Medical Dictionary Trie Project
License: MIT
"""

from __future__ import annotations
import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure src/ is importable from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dictionary import MedicalDictionary
from src.utils import benchmark, print_benchmark_report

# ──────────────────────────────────────────────────────────
# Setup Logging
# ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger("medical_trie.cli")

# ──────────────────────────────────────────────────────────
# ANSI Color Helpers
# ──────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"

def c(text: str, color: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{color}{text}{RESET}"


# ──────────────────────────────────────────────────────────
# BANNER
# ──────────────────────────────────────────────────────────

BANNER = f"""
{CYAN}{BOLD}
 ███╗   ███╗███████╗██████╗ ██╗ ██████╗ █████╗ ██╗
 ████╗ ████║██╔════╝██╔══██╗██║██╔════╝██╔══██╗██║
 ██╔████╔██║█████╗  ██║  ██║██║██║     ███████║██║
 ██║╚██╔╝██║██╔══╝  ██║  ██║██║██║     ██╔══██║██║
 ██║ ╚═╝ ██║███████╗██████╔╝██║╚██████╗██║  ██║███████╗
 ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝

      Medical Dictionary & Drug Lookup — Trie Engine
{RESET}"""


# ──────────────────────────────────────────────────────────
# CLI Session
# ──────────────────────────────────────────────────────────

class CLISession:
    """Interactive REPL session for the Medical Dictionary."""

    def __init__(
        self,
        data_file: str,
        mode: str = "autocomplete",
        top_k: int = 10,
        fuzzy_distance: int = 2,
    ) -> None:
        self.mode = mode
        self.top_k = top_k
        self.fuzzy_distance = fuzzy_distance

        # Load dictionary
        print(c("\n  Loading medical dictionary...", DIM))
        t0 = time.perf_counter()
        self.dict = MedicalDictionary(
            top_k=top_k,
            fuzzy_max_distance=fuzzy_distance,
        )
        try:
            inserted = self.dict.load_from_file(data_file)
        except FileNotFoundError:
            print(c(f"  ✗ Data file not found: {data_file}", RED))
            print(c("  Starting with empty dictionary.", YELLOW))
            inserted = 0

        elapsed = (time.perf_counter() - t0) * 1000
        print(
            c(f"  ✓ Loaded {inserted} terms in {elapsed:.1f} ms", GREEN)
        )
        print(
            c(f"  Dictionary size: {self.dict.size} unique terms", DIM)
        )

    def run(self) -> None:
        """Start the interactive REPL."""
        print(BANNER)
        self._print_help()

        while True:
            try:
                prompt = c(f"\n[{self.mode}] ", CYAN) + c("Search > ", BOLD)
                query = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print(c("\n\n  Goodbye! 👋\n", GREEN))
                break

            if not query:
                continue

            # Handle special commands
            if query.lower() in ("exit", "quit", "q"):
                print(c("\n  Goodbye! 👋\n", GREEN))
                break
            elif query.lower() == "help":
                self._print_help()
                continue
            elif query.lower() == "stats":
                self._print_stats()
                continue
            elif query.lower().startswith("mode "):
                self._switch_mode(query.split(" ", 1)[1].strip())
                continue
            elif query.lower().startswith("topk "):
                self._set_topk(query.split(" ", 1)[1].strip())
                continue
            elif query.lower() == "bench":
                self._run_benchmark(query)
                continue

            # Execute search based on current mode
            t0 = time.perf_counter()
            if self.mode == "autocomplete":
                self._do_autocomplete(query)
            elif self.mode == "fuzzy":
                self._do_fuzzy(query)
            elif self.mode == "search":
                self._do_search(query)
            elapsed = (time.perf_counter() - t0) * 1000
            print(c(f"\n  ⏱  {elapsed:.2f} ms", DIM))

    # ── Search Handlers ──────────────────────────────────

    def _do_autocomplete(self, prefix: str) -> None:
        results = self.dict.autocomplete(prefix, top_k=self.top_k)
        if not results:
            print(c(f"\n  No suggestions for '{prefix}'", YELLOW))
            print(c("  Tip: try 'mode fuzzy' for typo-tolerant search.", DIM))
            return
        print(c(f"\n  Suggestions for '{prefix}' ({len(results)} results):\n", BOLD))
        for i, (term, freq) in enumerate(results, 1):
            # Highlight the matching prefix in the term
            highlighted = c(term[:len(prefix)], CYAN) + term[len(prefix):]
            print(f"   {c(str(i).rjust(2), DIM)}. {highlighted}  {c(f'(×{freq})', DIM)}")

    def _do_fuzzy(self, query: str) -> None:
        results = self.dict.fuzzy_search(
            query, top_k=self.top_k, max_distance=self.fuzzy_distance
        )
        if not results:
            print(c(f"\n  No fuzzy matches for '{query}' (max dist={self.fuzzy_distance})", YELLOW))
            return
        print(c(f"\n  Fuzzy matches for '{query}' (dist ≤ {self.fuzzy_distance}):\n", BOLD))
        for i, (term, dist) in enumerate(results, 1):
            dist_label = c(f"dist={dist}", GREEN if dist == 0 else YELLOW)
            print(f"   {c(str(i).rjust(2), DIM)}. {term}  {c('[' + str(dist_label) + ']', DIM)}")

    def _do_search(self, term: str) -> None:
        found = self.dict.search(term)
        if found:
            print(c(f"\n  ✓ '{term}' found in the dictionary.", GREEN))
        else:
            print(c(f"\n  ✗ '{term}' NOT found.", RED))
            # Suggest autocomplete anyway
            suggestions = self.dict.autocomplete_terms(term, top_k=5)
            if suggestions:
                print(c("\n  Did you mean:", YELLOW))
                for s in suggestions:
                    print(f"    • {s}")

    # ── Commands ─────────────────────────────────────────

    def _print_stats(self) -> None:
        s = self.dict.stats()
        print(c("\n  ── Dictionary Statistics ──────────────", CYAN))
        print(f"  Terms loaded    : {c(str(s['total_terms']), GREEN)}")
        print(f"  Trie nodes      : {c(str(s['total_nodes']), GREEN)}")
        print(f"  Memory estimate : {c(str(s['memory_estimate_kb']) + ' KB', GREEN)}")
        if s["loaded_files"]:
            for f in s["loaded_files"]:
                print(f"  Data file       : {c(f, DIM)}")

    def _switch_mode(self, new_mode: str) -> None:
        valid = ("autocomplete", "fuzzy", "search")
        if new_mode not in valid:
            print(c(f"  Unknown mode '{new_mode}'. Valid: {', '.join(valid)}", RED))
            return
        self.mode = new_mode
        print(c(f"  Switched to '{self.mode}' mode.", GREEN))

    def _set_topk(self, value: str) -> None:
        try:
            k = int(value)
            if k < 1 or k > 100:
                raise ValueError
            self.top_k = k
            self.dict._top_k = k
            print(c(f"  Top-K set to {k}.", GREEN))
        except ValueError:
            print(c("  Invalid value. Use an integer between 1 and 100.", RED))

    def _run_benchmark(self, _: str) -> None:
        print(c("\n  Running benchmarks...", YELLOW))
        test_prefix = "dia"
        stats_insert = benchmark(self.dict.add_term, "test_benchmark_term", iterations=1000)
        self.dict.remove_term("test_benchmark_term")
        stats_ac = benchmark(self.dict.autocomplete, test_prefix, iterations=1000)
        print_benchmark_report(f"Insert term", stats_insert)
        print_benchmark_report(f"Autocomplete (prefix='{test_prefix}')", stats_ac)

    def _print_help(self) -> None:
        print(c("""
  ┌─────────────────────────────────────────────────────────┐
  │                     COMMANDS                            │
  ├─────────────────────────────────────────────────────────┤
  │  <query>               Search using current mode        │
  │  mode autocomplete     Switch to prefix autocomplete    │
  │  mode fuzzy            Switch to fuzzy/typo search      │
  │  mode search           Switch to exact-match search     │
  │  topk <n>              Set max results (1–100)          │
  │  stats                 Show dictionary statistics       │
  │  bench                 Run performance benchmark        │
  │  help                  Show this help message           │
  │  exit / quit / q       Exit the CLI                     │
  └─────────────────────────────────────────────────────────┘
""", DIM))


# ──────────────────────────────────────────────────────────
# Argument Parser
# ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="medical-trie",
        description="Medical Dictionary & Drug Lookup using Trie",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cli.main
  python -m cli.main --data data/sample_medical_terms.txt
  python -m cli.main --mode fuzzy --topk 5
        """,
    )
    parser.add_argument(
        "--data",
        default=str(
            Path(__file__).resolve().parent.parent / "data" / "sample_medical_terms.txt"
        ),
        help="Path to medical terms file (default: data/sample_medical_terms.txt)",
    )
    parser.add_argument(
        "--mode",
        choices=["autocomplete", "fuzzy", "search"],
        default="autocomplete",
        help="Initial search mode (default: autocomplete)",
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=10,
        help="Max suggestions to display (default: 10)",
    )
    parser.add_argument(
        "--fuzzy-distance",
        type=int,
        default=2,
        help="Max Levenshtein distance for fuzzy search (default: 2)",
    )
    return parser.parse_args()


# ──────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    session = CLISession(
        data_file=args.data,
        mode=args.mode,
        top_k=args.topk,
        fuzzy_distance=args.fuzzy_distance,
    )
    session.run()


if __name__ == "__main__":
    main()
