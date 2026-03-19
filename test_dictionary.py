"""
test_dictionary.py - Unit Tests for MedicalDictionary Module

Tests cover:
  - File loading (success, missing file, duplicates)
  - List loading
  - Normalization (case, whitespace)
  - search() exact match
  - autocomplete() correctness
  - fuzzy_search() typo tolerance
  - add_term() / remove_term()
  - Stats and introspection

Run with:
    pytest tests/test_dictionary.py -v

Author: Medical Dictionary Trie Project
License: MIT
"""

import sys
import tempfile
import os
from pathlib import Path
from typing import List

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dictionary import MedicalDictionary


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

SAMPLE_TERMS: List[str] = [
    "Diabetes Mellitus",
    "DIABETES MELLITUS",          # duplicate (different case)
    "  Diabetic Neuropathy  ",    # leading/trailing spaces
    "Hypertension",
    "Cardiac Arrest",
    "Cardiomyopathy",
    "asthma",
    "Pneumonia",
    "Anemia",
    "Leukemia",
]

EXPECTED_UNIQUE = 9  # after normalization: 9 unique terms


@pytest.fixture
def empty_dict() -> MedicalDictionary:
    return MedicalDictionary()


@pytest.fixture
def loaded_dict() -> MedicalDictionary:
    d = MedicalDictionary(top_k=10)
    d.load_from_list(SAMPLE_TERMS)
    return d


@pytest.fixture
def temp_terms_file(tmp_path: Path) -> str:
    """Write SAMPLE_TERMS to a temporary file and return its path."""
    filepath = tmp_path / "test_terms.txt"
    filepath.write_text("\n".join(SAMPLE_TERMS), encoding="utf-8")
    return str(filepath)


# ──────────────────────────────────────────────────────────
# Loading Tests
# ──────────────────────────────────────────────────────────

class TestMedicalDictionaryLoading:
    def test_load_from_list(self, empty_dict):
        inserted = empty_dict.load_from_list(["asthma", "cancer"])
        assert inserted == 2
        assert empty_dict.size == 2

    def test_load_from_list_deduplicates(self, empty_dict):
        inserted = empty_dict.load_from_list(["asthma", "asthma", "ASTHMA"])
        assert inserted == 1  # All three normalize to "asthma"
        assert empty_dict.size == 1

    def test_load_from_list_skips_empty_lines(self, empty_dict):
        inserted = empty_dict.load_from_list(["asthma", "", "  ", "cancer"])
        assert inserted == 2

    def test_load_from_file_success(self, empty_dict, temp_terms_file):
        inserted = empty_dict.load_from_file(temp_terms_file)
        assert inserted == EXPECTED_UNIQUE

    def test_load_from_file_missing_raises(self, empty_dict):
        with pytest.raises(FileNotFoundError):
            empty_dict.load_from_file("/nonexistent/path/file.txt")

    def test_load_multiple_files_accumulates(self, empty_dict, temp_terms_file):
        empty_dict.load_from_file(temp_terms_file)
        # Create a second file with new terms
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("appendicitis\nbronchitis\n")
            second_file = f.name
        try:
            empty_dict.load_from_file(second_file)
            assert empty_dict.size == EXPECTED_UNIQUE + 2
        finally:
            os.unlink(second_file)

    def test_loaded_files_tracked(self, empty_dict, temp_terms_file):
        empty_dict.load_from_file(temp_terms_file)
        stats = empty_dict.stats()
        assert any(temp_terms_file in f for f in stats["loaded_files"])


# ──────────────────────────────────────────────────────────
# Normalization Tests
# ──────────────────────────────────────────────────────────

class TestNormalization:
    def test_case_insensitive_insert(self, empty_dict):
        empty_dict.load_from_list(["DIABETES", "diabetes", "Diabetes"])
        assert empty_dict.size == 1

    def test_whitespace_stripped(self, empty_dict):
        empty_dict.load_from_list(["  asthma  "])
        assert empty_dict.search("asthma")

    def test_internal_spaces_collapsed(self, empty_dict):
        empty_dict.load_from_list(["diabetes  mellitus"])
        assert empty_dict.search("diabetes mellitus")

    def test_search_case_insensitive(self, loaded_dict):
        assert loaded_dict.search("DIABETES MELLITUS")
        assert loaded_dict.search("Diabetes Mellitus")
        assert loaded_dict.search("diabetes mellitus")

    def test_search_trims_whitespace(self, loaded_dict):
        assert loaded_dict.search("  hypertension  ")


# ──────────────────────────────────────────────────────────
# Search Tests
# ──────────────────────────────────────────────────────────

class TestDictionarySearch:
    def test_search_found(self, loaded_dict):
        assert loaded_dict.search("hypertension") is True

    def test_search_not_found(self, loaded_dict):
        assert loaded_dict.search("appendicitis") is False

    def test_search_empty_string(self, loaded_dict):
        assert loaded_dict.search("") is False

    def test_contains_operator(self, loaded_dict):
        assert "hypertension" in loaded_dict
        assert "appendicitis" not in loaded_dict

    def test_starts_with_true(self, loaded_dict):
        assert loaded_dict.starts_with("card") is True

    def test_starts_with_false(self, loaded_dict):
        assert loaded_dict.starts_with("xyz") is False


# ──────────────────────────────────────────────────────────
# Autocomplete Tests
# ──────────────────────────────────────────────────────────

class TestDictionaryAutocomplete:
    def test_autocomplete_returns_matching_terms(self, loaded_dict):
        results = loaded_dict.autocomplete("card")
        terms = [t for t, _ in results]
        assert "cardiac arrest" in terms
        assert "cardiomyopathy" in terms

    def test_autocomplete_returns_empty_for_unknown_prefix(self, loaded_dict):
        results = loaded_dict.autocomplete("xyz")
        assert results == []

    def test_autocomplete_top_k_respected(self, loaded_dict):
        results = loaded_dict.autocomplete("a", top_k=1)
        assert len(results) == 1

    def test_autocomplete_terms_returns_strings(self, loaded_dict):
        terms = loaded_dict.autocomplete_terms("card")
        assert all(isinstance(t, str) for t in terms)

    def test_autocomplete_case_insensitive_prefix(self, loaded_dict):
        results_lower = loaded_dict.autocomplete("card")
        results_upper = loaded_dict.autocomplete("CARD")
        assert results_lower == results_upper

    def test_autocomplete_alphabetical_sort(self, loaded_dict):
        results = loaded_dict.autocomplete("card", sort_by="alphabetical")
        terms = [t for t, _ in results]
        assert terms == sorted(terms)

    def test_autocomplete_full_term_as_prefix(self, loaded_dict):
        # "anemia" is a term AND starts with itself
        results = loaded_dict.autocomplete("anemia")
        terms = [t for t, _ in results]
        assert "anemia" in terms

    def test_format_autocomplete_returns_string(self, loaded_dict):
        output = loaded_dict.format_autocomplete("card")
        assert isinstance(output, str)
        assert "cardiac arrest" in output or "cardiomyopathy" in output


# ──────────────────────────────────────────────────────────
# Fuzzy Search Tests
# ──────────────────────────────────────────────────────────

class TestFuzzySearch:
    def test_fuzzy_exact_match_via_prefix(self, loaded_dict):
        """Exact prefix → fast path, distance 0."""
        results = loaded_dict.fuzzy_search("diab")
        assert len(results) > 0
        for _, dist in results:
            assert dist == 0

    def test_fuzzy_typo_tolerance(self, empty_dict):
        """'diabets' (1 typo) should match 'diabetes mellitus'."""
        empty_dict.load_from_list(["diabetes mellitus"])
        results = empty_dict.fuzzy_search("diabets mellitus", max_distance=2)
        terms = [t for t, _ in results]
        assert "diabetes mellitus" in terms

    def test_fuzzy_no_match_beyond_distance(self, empty_dict):
        """Very different string should not match."""
        empty_dict.load_from_list(["diabetes"])
        results = empty_dict.fuzzy_search("xxxxxxxxxx", max_distance=1)
        assert results == []

    def test_fuzzy_returns_top_k(self, loaded_dict):
        results = loaded_dict.fuzzy_search("a", top_k=3)
        assert len(results) <= 3

    def test_fuzzy_empty_query(self, loaded_dict):
        results = loaded_dict.fuzzy_search("")
        assert results == []

    def test_fuzzy_distance_zero_is_exact(self, empty_dict):
        """max_distance=0 should only return prefix matches."""
        empty_dict.load_from_list(["diabetes"])
        results = empty_dict.fuzzy_search("diabetex", max_distance=0)
        # "diabetex" is not a prefix of "diabetes"
        # and Levenshtein distance to "diabetes" = 1 > 0
        assert results == []


# ──────────────────────────────────────────────────────────
# Mutation Tests
# ──────────────────────────────────────────────────────────

class TestMutations:
    def test_add_term(self, loaded_dict):
        initial_size = loaded_dict.size
        result = loaded_dict.add_term("appendicitis")
        assert result is True
        assert loaded_dict.size == initial_size + 1
        assert loaded_dict.search("appendicitis")

    def test_add_duplicate_term(self, loaded_dict):
        loaded_dict.add_term("appendicitis")
        result = loaded_dict.add_term("appendicitis")
        assert result is False

    def test_add_empty_term(self, loaded_dict):
        result = loaded_dict.add_term("")
        assert result is False

    def test_remove_existing_term(self, loaded_dict):
        initial_size = loaded_dict.size
        result = loaded_dict.remove_term("hypertension")
        assert result is True
        assert loaded_dict.size == initial_size - 1
        assert not loaded_dict.search("hypertension")

    def test_remove_nonexistent_term(self, loaded_dict):
        result = loaded_dict.remove_term("appendicitis")
        assert result is False

    def test_remove_term_does_not_affect_autocomplete(self, loaded_dict):
        loaded_dict.remove_term("cardiac arrest")
        results = loaded_dict.autocomplete("card")
        terms = [t for t, _ in results]
        assert "cardiac arrest" not in terms
        assert "cardiomyopathy" in terms


# ──────────────────────────────────────────────────────────
# Stats / Introspection Tests
# ──────────────────────────────────────────────────────────

class TestStats:
    def test_size_property(self, loaded_dict):
        assert loaded_dict.size == EXPECTED_UNIQUE

    def test_len_operator(self, loaded_dict):
        assert len(loaded_dict) == EXPECTED_UNIQUE

    def test_stats_dict_keys(self, loaded_dict):
        s = loaded_dict.stats()
        assert "total_terms" in s
        assert "total_nodes" in s
        assert "loaded_files" in s
        assert "memory_estimate_kb" in s

    def test_stats_total_terms_matches_size(self, loaded_dict):
        assert loaded_dict.stats()["total_terms"] == loaded_dict.size

    def test_get_all_terms_sorted(self, loaded_dict):
        all_terms = loaded_dict.get_all_terms()
        assert all_terms == sorted(all_terms)

    def test_get_all_terms_count(self, loaded_dict):
        assert len(loaded_dict.get_all_terms()) == loaded_dict.size

    def test_repr(self, loaded_dict):
        r = repr(loaded_dict)
        assert "MedicalDictionary(" in r

    def test_node_count_positive(self, loaded_dict):
        assert loaded_dict.node_count > 0
        assert loaded_dict.node_count >= loaded_dict.size
