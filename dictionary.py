"""
dictionary.py - Medical Dictionary Module

High-level interface that combines the Trie with:
  - File-based dataset loading
  - Text normalization
  - Duplicate handling
  - Fuzzy search (typo tolerance via Levenshtein)
  - Ranked autocomplete

Author: Medical Dictionary Trie Project
License: MIT
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from src.trie import Trie
from src.utils import (
    normalize_term,
    normalize_prefix,
    fuzzy_match,
    load_lines_from_file,
    format_suggestions,
)

logger = logging.getLogger(__name__)


class MedicalDictionary:
    """
    High-level Medical Dictionary backed by an optimized Trie.

    Features:
      - Load terms from a flat text file (one term per line)
      - Case-insensitive, normalized storage
      - Fast prefix autocomplete via Trie
      - Fuzzy search for typo correction
      - Top-k ranked results (by frequency or alphabetically)

    Usage:
        >>> d = MedicalDictionary()
        >>> d.load_from_file("data/sample_medical_terms.txt")
        >>> d.autocomplete("diab")
        [('diabetes mellitus', 2), ('diabetic ketoacidosis', 1), ...]
    """

    def __init__(
        self,
        top_k: int = 10,
        fuzzy_max_distance: int = 2,
        sort_by: str = "frequency",
    ) -> None:
        """
        Initialize the Medical Dictionary.

        Args:
            top_k:              Default number of results to return.
            fuzzy_max_distance: Max Levenshtein distance for fuzzy matches.
            sort_by:            Default sort strategy ("frequency" or "alphabetical").
        """
        self._trie = Trie()
        self._top_k = top_k
        self._fuzzy_max_distance = fuzzy_max_distance
        self._sort_by = sort_by
        self._loaded_files: List[str] = []

        logger.info(
            "MedicalDictionary initialized (top_k=%d, fuzzy_dist=%d, sort=%s)",
            top_k, fuzzy_max_distance, sort_by,
        )

    # ──────────────────────────────────────────────
    # LOADING
    # ──────────────────────────────────────────────

    def load_from_file(self, filepath: str) -> int:
        """
        Load medical terms from a plain-text file (one term per line).

        Lines that are empty or become empty after normalization are skipped.
        Duplicate terms are handled gracefully (frequency incremented).

        Args:
            filepath: Path to the .txt file containing medical terms.

        Returns:
            Number of unique new terms inserted.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        raw_lines = load_lines_from_file(filepath)
        inserted = self._bulk_insert(raw_lines)
        self._loaded_files.append(str(path.resolve()))

        logger.info(
            "Loaded '%s': %d raw lines → %d unique new terms inserted",
            filepath, len(raw_lines), inserted,
        )
        return inserted

    def load_from_list(self, terms: List[str]) -> int:
        """
        Bulk-insert terms from a Python list.

        Args:
            terms: List of medical term strings.

        Returns:
            Number of unique new terms inserted.
        """
        inserted = self._bulk_insert(terms)
        logger.info(
            "Loaded from list: %d input items → %d unique new terms",
            len(terms), inserted,
        )
        return inserted

    def _bulk_insert(self, raw_terms: List[str]) -> int:
        """
        Normalize and insert a list of raw term strings.

        Args:
            raw_terms: List of un-normalized term strings.

        Returns:
            Count of newly inserted (not duplicate) terms.
        """
        inserted = 0
        for raw in raw_terms:
            normalized = normalize_term(raw)
            if normalized:  # Skip blank lines
                if self._trie.insert(normalized):
                    inserted += 1
        return inserted

    # ──────────────────────────────────────────────
    # SEARCH
    # ──────────────────────────────────────────────

    def search(self, term: str) -> bool:
        """
        Exact-match lookup (case-insensitive).

        Args:
            term: The term to search for.

        Returns:
            True if the term exists in the dictionary.
        """
        return self._trie.search(normalize_term(term))

    def starts_with(self, prefix: str) -> bool:
        """
        Check if any stored term begins with this prefix.

        Args:
            prefix: Search prefix.

        Returns:
            True if at least one matching term exists.
        """
        return self._trie.starts_with(normalize_prefix(prefix))

    # ──────────────────────────────────────────────
    # AUTOCOMPLETE
    # ──────────────────────────────────────────────

    def autocomplete(
        self,
        prefix: str,
        top_k: Optional[int] = None,
        sort_by: Optional[str] = None,
    ) -> List[Tuple[str, int]]:
        """
        Return autocomplete suggestions for the given prefix.

        Args:
            prefix:  The search prefix (will be normalized internally).
            top_k:   Max number of results (defaults to self._top_k).
            sort_by: Sort strategy ("frequency" or "alphabetical").

        Returns:
            List of (term, frequency) tuples, ranked by sort_by.
        """
        normalized = normalize_prefix(prefix)
        if not normalized:
            return []

        k = top_k if top_k is not None else self._top_k
        strategy = sort_by if sort_by is not None else self._sort_by

        results = self._trie.autocomplete(normalized, top_k=k, sort_by=strategy)
        logger.debug(
            "autocomplete('%s') → %d results (top_k=%d)", prefix, len(results), k
        )
        return results

    def autocomplete_terms(
        self,
        prefix: str,
        top_k: Optional[int] = None,
    ) -> List[str]:
        """
        Convenience method — returns only the term strings (no frequencies).

        Args:
            prefix: The search prefix.
            top_k:  Max results.

        Returns:
            List of term strings.
        """
        return [term for term, _ in self.autocomplete(prefix, top_k=top_k)]

    # ──────────────────────────────────────────────
    # FUZZY SEARCH
    # ──────────────────────────────────────────────

    def fuzzy_search(
        self,
        query: str,
        top_k: Optional[int] = None,
        max_distance: Optional[int] = None,
    ) -> List[Tuple[str, int]]:
        """
        Fuzzy search using Levenshtein distance — tolerates typos.

        Strategy:
          1. Try prefix autocomplete first (fast path).
          2. If prefix yields no results, fall back to fuzzy matching
             against all stored terms (slower, O(N)).

        Args:
            query:        The search string (possibly misspelled).
            top_k:        Max results (defaults to self._top_k).
            max_distance: Max edit distance (defaults to self._fuzzy_max_distance).

        Returns:
            List of (term, edit_distance) tuples sorted by distance ascending.
            NOTE: For the fast prefix path, distances are set to 0.
        """
        normalized_query = normalize_term(query)
        if not normalized_query:
            return []

        k = top_k if top_k is not None else self._top_k
        max_dist = max_distance if max_distance is not None else self._fuzzy_max_distance

        # Fast path: try prefix autocomplete first
        prefix_results = self._trie.autocomplete(normalized_query, top_k=k)
        if prefix_results:
            logger.debug("fuzzy_search fast path: %d prefix results", len(prefix_results))
            return [(term, 0) for term, _ in prefix_results[:k]]

        # Slow path: Levenshtein against all stored terms
        logger.debug(
            "fuzzy_search falling back to Levenshtein for query '%s'", query
        )
        all_terms = self._trie.get_all_terms()
        matches = fuzzy_match(normalized_query, all_terms, max_distance=max_dist, top_k=k)

        return matches

    # ──────────────────────────────────────────────
    # MUTATION
    # ──────────────────────────────────────────────

    def add_term(self, term: str) -> bool:
        """
        Add a single term to the dictionary.

        Args:
            term: The term to add.

        Returns:
            True if the term was newly inserted, False if duplicate.
        """
        normalized = normalize_term(term)
        if not normalized:
            return False
        result = self._trie.insert(normalized)
        if result:
            logger.info("Added new term: '%s'", normalized)
        return result

    def remove_term(self, term: str) -> bool:
        """
        Remove a term from the dictionary.

        Args:
            term: The term to remove.

        Returns:
            True if deleted, False if term was not found.
        """
        normalized = normalize_term(term)
        result = self._trie.delete(normalized)
        if result:
            logger.info("Removed term: '%s'", normalized)
        return result

    # ──────────────────────────────────────────────
    # STATS / INTROSPECTION
    # ──────────────────────────────────────────────

    @property
    def size(self) -> int:
        """Total number of unique terms stored."""
        return self._trie.size

    @property
    def node_count(self) -> int:
        """Total number of Trie nodes allocated."""
        return self._trie.node_count

    def stats(self) -> dict:
        """
        Return a statistics dictionary about the dictionary.

        Returns:
            Dict with size, node_count, loaded_files, and memory_estimate_kb.
        """
        # Rough memory estimate: each node ≈ 200 bytes (Python dict overhead)
        memory_estimate_kb = round((self._trie.node_count * 200) / 1024, 2)
        return {
            "total_terms": self._trie.size,
            "total_nodes": self._trie.node_count,
            "loaded_files": self._loaded_files,
            "memory_estimate_kb": memory_estimate_kb,
        }

    def get_all_terms(self) -> List[str]:
        """Return all stored terms in alphabetical order."""
        return self._trie.get_all_terms()

    def format_autocomplete(self, prefix: str, top_k: int = 10) -> str:
        """
        Return a formatted string of autocomplete results (for CLI display).

        Args:
            prefix: Search prefix.
            top_k:  Max results.

        Returns:
            Human-readable formatted string.
        """
        suggestions = self.autocomplete(prefix, top_k=top_k)
        return format_suggestions(suggestions)

    def __len__(self) -> int:
        return self._trie.size

    def __contains__(self, term: str) -> bool:
        return self.search(term)

    def __repr__(self) -> str:
        return (
            f"MedicalDictionary("
            f"terms={self._trie.size}, "
            f"nodes={self._trie.node_count})"
        )
