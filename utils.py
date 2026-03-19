"""
utils.py - Utility Functions for Medical Dictionary Trie

Includes:
  - Text normalization (lowercase, strip, clean)
  - Levenshtein distance (fuzzy search)
  - Top-k filtering
  - Benchmarking helpers

Author: Medical Dictionary Trie Project
License: MIT
"""

from __future__ import annotations
import re
import time
import logging
from typing import List, Tuple, Callable, Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# TEXT NORMALIZATION
# ──────────────────────────────────────────────────────────

def normalize_term(term: str) -> str:
    """
    Normalize a medical term for consistent storage and lookup.

    Steps:
      1. Strip leading/trailing whitespace
      2. Convert to lowercase
      3. Collapse multiple internal spaces into one
      4. Remove non-alphanumeric characters except spaces and hyphens

    Args:
        term: Raw input string.

    Returns:
        Normalized string, or empty string if input is empty/invalid.
    """
    if not isinstance(term, str):
        return ""

    term = term.strip().lower()
    # Collapse multiple spaces
    term = re.sub(r"\s+", " ", term)
    # Allow letters, digits, spaces, hyphens (common in medical terms)
    term = re.sub(r"[^a-z0-9 \-]", "", term)
    return term


def normalize_prefix(prefix: str) -> str:
    """
    Normalize a search prefix (same pipeline as normalize_term).

    Args:
        prefix: Raw prefix string from user input.

    Returns:
        Normalized prefix string.
    """
    return normalize_term(prefix)


# ──────────────────────────────────────────────────────────
# LEVENSHTEIN DISTANCE (Fuzzy Search)
# ──────────────────────────────────────────────────────────

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Compute the Levenshtein edit distance between two strings.

    Uses dynamic programming with space optimization (two-row DP).

    Time Complexity:  O(m * n)
    Space Complexity: O(min(m, n))

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Minimum number of single-character edits (insert, delete, substitute)
        needed to transform s1 into s2.

    Example:
        >>> levenshtein_distance("diabets", "diabetes")
        1
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Ensure s1 is the shorter string for space optimization
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    len1, len2 = len(s1), len(s2)
    prev_row = list(range(len1 + 1))

    for j in range(1, len2 + 1):
        curr_row = [j] + [0] * len1
        for i in range(1, len1 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[i] = min(
                prev_row[i] + 1,        # deletion
                curr_row[i - 1] + 1,    # insertion
                prev_row[i - 1] + cost  # substitution
            )
        prev_row = curr_row

    return prev_row[len1]


def fuzzy_match(
    query: str,
    candidates: List[str],
    max_distance: int = 2,
    top_k: int = 10
) -> List[Tuple[str, int]]:
    """
    Find the closest matches to `query` among `candidates` using
    Levenshtein distance.

    Args:
        query:        The search query (potentially misspelled).
        candidates:   List of candidate strings to compare against.
        max_distance: Maximum edit distance to consider a match (default 2).
        top_k:        Maximum number of results to return.

    Returns:
        List of (term, distance) tuples sorted by distance ascending.
    """
    matches: List[Tuple[str, int]] = []

    for candidate in candidates:
        dist = levenshtein_distance(query, candidate)
        if dist <= max_distance:
            matches.append((candidate, dist))

    # Sort by distance, then alphabetically for tie-breaking
    matches.sort(key=lambda x: (x[0], x[1]))
    return matches[:top_k]


# ──────────────────────────────────────────────────────────
# RANKING HELPERS
# ──────────────────────────────────────────────────────────

def rank_results(
    results: List[Tuple[str, int]],
    sort_by: str = "frequency",
    top_k: int = 10
) -> List[str]:
    """
    Rank and filter autocomplete results.

    Args:
        results: List of (term, frequency) tuples.
        sort_by: "frequency" (default) or "alphabetical".
        top_k:   Maximum results to return.

    Returns:
        Sorted list of term strings.
    """
    if sort_by == "frequency":
        ranked = sorted(results, key=lambda x: (-x[1], x[0]))
    else:
        ranked = sorted(results, key=lambda x: x[0])

    return [term for term, _ in ranked[:top_k]]


# ──────────────────────────────────────────────────────────
# BENCHMARKING
# ──────────────────────────────────────────────────────────

def benchmark(func: Callable, *args: Any, iterations: int = 100) -> dict:
    """
    Benchmark a function call over multiple iterations.

    Args:
        func:       The function to benchmark.
        *args:      Arguments to pass to the function.
        iterations: Number of times to run the function.

    Returns:
        Dictionary containing:
          - total_ms:   Total elapsed time in milliseconds
          - avg_ms:     Average time per call in milliseconds
          - min_ms:     Minimum call time in milliseconds
          - max_ms:     Maximum call time in milliseconds
          - iterations: Number of iterations run
    """
    times: List[float] = []

    for _ in range(iterations):
        start = time.perf_counter()
        func(*args)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return {
        "total_ms": round(sum(times), 4),
        "avg_ms": round(sum(times) / len(times), 4),
        "min_ms": round(min(times), 4),
        "max_ms": round(max(times), 4),
        "iterations": iterations,
    }


def print_benchmark_report(label: str, stats: dict) -> None:
    """
    Pretty-print a benchmark report.

    Args:
        label: Description of the operation being benchmarked.
        stats: Output dict from benchmark().
    """
    print(f"\n{'─' * 50}")
    print(f"  Benchmark: {label}")
    print(f"{'─' * 50}")
    print(f"  Iterations : {stats['iterations']}")
    print(f"  Total      : {stats['total_ms']} ms")
    print(f"  Average    : {stats['avg_ms']} ms/call")
    print(f"  Min        : {stats['min_ms']} ms")
    print(f"  Max        : {stats['max_ms']} ms")
    print(f"{'─' * 50}")


# ──────────────────────────────────────────────────────────
# I/O HELPERS
# ──────────────────────────────────────────────────────────

def load_lines_from_file(filepath: str) -> List[str]:
    """
    Read all non-empty lines from a text file.

    Args:
        filepath: Path to the text file.

    Returns:
        List of raw string lines (not normalized).

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: On any other read error.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f if line.strip()]
        logger.info("Loaded %d lines from '%s'", len(lines), filepath)
        return lines
    except FileNotFoundError:
        logger.error("File not found: %s", filepath)
        raise
    except IOError as exc:
        logger.error("Failed to read '%s': %s", filepath, exc)
        raise


def format_suggestions(suggestions: List[Tuple[str, int]]) -> str:
    """
    Format autocomplete suggestions for CLI display.

    Args:
        suggestions: List of (term, frequency) tuples.

    Returns:
        Formatted multi-line string.
    """
    if not suggestions:
        return "  No suggestions found."

    lines = []
    for i, (term, freq) in enumerate(suggestions, start=1):
        lines.append(f"  {i:2}. {term}  (freq: {freq})")
    return "\n".join(lines)
