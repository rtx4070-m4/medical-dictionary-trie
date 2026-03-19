"""
test_trie.py - Unit Tests for Trie Data Structure

Tests cover:
  - Insert (new, duplicate)
  - Search (found, not found, case)
  - starts_with / prefix check
  - Autocomplete (correctness, top-k, sorting)
  - Delete (existing, non-existing, orphan cleanup)
  - Edge cases (empty strings, single characters, long strings)
  - Size tracking and node counts

Run with:
    pytest tests/test_trie.py -v

Author: Medical Dictionary Trie Project
License: MIT
"""

import sys
from pathlib import Path
import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.trie import Trie, TrieNode


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def empty_trie() -> Trie:
    """Return a fresh empty Trie."""
    return Trie()


@pytest.fixture
def populated_trie() -> Trie:
    """Return a Trie pre-loaded with common medical terms."""
    t = Trie()
    terms = [
        "diabetes",
        "diabetes mellitus",
        "diabetic neuropathy",
        "diarrhea",
        "diphtheria",
        "cancer",
        "cardiac arrest",
        "cardiomyopathy",
        "hypertension",
        "hypothyroidism",
        "hypoglycemia",
        "asthma",
    ]
    for term in terms:
        t.insert(term)
    return t


# ──────────────────────────────────────────────────────────
# TrieNode Tests
# ──────────────────────────────────────────────────────────

class TestTrieNode:
    def test_default_state(self):
        node = TrieNode()
        assert node.children == {}
        assert node.is_end is False
        assert node.frequency == 0
        assert node.term is None

    def test_children_are_independent(self):
        """Ensure each node's children dict is independent."""
        n1 = TrieNode()
        n2 = TrieNode()
        n1.children["a"] = TrieNode()
        assert "a" not in n2.children


# ──────────────────────────────────────────────────────────
# Insert Tests
# ──────────────────────────────────────────────────────────

class TestTrieInsert:
    def test_insert_single_term(self, empty_trie):
        result = empty_trie.insert("diabetes")
        assert result is True
        assert empty_trie.size == 1

    def test_insert_multiple_terms(self, empty_trie):
        terms = ["asthma", "cancer", "diabetes"]
        for t in terms:
            empty_trie.insert(t)
        assert empty_trie.size == 3

    def test_insert_duplicate_returns_false(self, empty_trie):
        empty_trie.insert("diabetes")
        result = empty_trie.insert("diabetes")
        assert result is False
        assert empty_trie.size == 1

    def test_insert_duplicate_increments_frequency(self, empty_trie):
        empty_trie.insert("diabetes")
        empty_trie.insert("diabetes")
        node = empty_trie._find_node("diabetes")
        assert node is not None
        assert node.frequency == 2

    def test_insert_empty_string_returns_false(self, empty_trie):
        result = empty_trie.insert("")
        assert result is False
        assert empty_trie.size == 0

    def test_insert_single_character(self, empty_trie):
        result = empty_trie.insert("a")
        assert result is True
        assert empty_trie.size == 1

    def test_insert_updates_node_count(self, empty_trie):
        initial_nodes = empty_trie.node_count
        empty_trie.insert("abc")
        assert empty_trie.node_count == initial_nodes + 3  # a, b, c

    def test_insert_shared_prefix_shares_nodes(self, empty_trie):
        empty_trie.insert("car")
        empty_trie.insert("card")
        # 'car' path already exists, only 'd' is a new node
        assert empty_trie.node_count == 5  # root + c + a + r + d

    def test_insert_stores_term_on_end_node(self, empty_trie):
        empty_trie.insert("diabetes")
        node = empty_trie._find_node("diabetes")
        assert node.term == "diabetes"

    def test_insert_long_term(self, empty_trie):
        long_term = "autoimmune polyendocrinopathy candidiasis ectodermal dystrophy"
        result = empty_trie.insert(long_term)
        assert result is True
        assert empty_trie.search(long_term)


# ──────────────────────────────────────────────────────────
# Search Tests
# ──────────────────────────────────────────────────────────

class TestTrieSearch:
    def test_search_existing_term(self, populated_trie):
        assert populated_trie.search("diabetes") is True

    def test_search_nonexistent_term(self, populated_trie):
        assert populated_trie.search("appendicitis") is False

    def test_search_prefix_is_not_match(self, populated_trie):
        # "diab" is a prefix but not a complete term
        assert populated_trie.search("diab") is False

    def test_search_superstring_is_not_match(self, populated_trie):
        # "diabetesXYZ" should not match
        assert populated_trie.search("diabetesXYZ") is False

    def test_search_empty_string(self, populated_trie):
        assert populated_trie.search("") is False

    def test_search_case_sensitivity(self, empty_trie):
        # Trie is case-sensitive at this layer (normalization done in MedicalDictionary)
        empty_trie.insert("diabetes")
        assert empty_trie.search("diabetes") is True
        assert empty_trie.search("Diabetes") is False  # Trie itself is case-sensitive

    def test_search_after_insert(self, empty_trie):
        assert empty_trie.search("hypertension") is False
        empty_trie.insert("hypertension")
        assert empty_trie.search("hypertension") is True

    def test_in_operator(self, populated_trie):
        assert "diabetes" in populated_trie
        assert "xyz" not in populated_trie

    def test_get_frequency(self, empty_trie):
        empty_trie.insert("asthma")
        empty_trie.insert("asthma")
        assert empty_trie.get_frequency("asthma") == 2

    def test_get_frequency_nonexistent(self, empty_trie):
        assert empty_trie.get_frequency("nothing") == 0


# ──────────────────────────────────────────────────────────
# Starts-With Tests
# ──────────────────────────────────────────────────────────

class TestTrieStartsWith:
    def test_starts_with_valid_prefix(self, populated_trie):
        assert populated_trie.starts_with("dia") is True

    def test_starts_with_full_term(self, populated_trie):
        assert populated_trie.starts_with("diabetes") is True

    def test_starts_with_nonexistent_prefix(self, populated_trie):
        assert populated_trie.starts_with("xyz") is False

    def test_starts_with_empty_string(self, populated_trie):
        # Root always matches (every term starts with "")
        assert populated_trie.starts_with("") is True

    def test_starts_with_single_char(self, populated_trie):
        assert populated_trie.starts_with("a") is True
        assert populated_trie.starts_with("z") is False


# ──────────────────────────────────────────────────────────
# Autocomplete Tests
# ──────────────────────────────────────────────────────────

class TestTrieAutocomplete:
    def test_autocomplete_returns_correct_terms(self, populated_trie):
        results = populated_trie.autocomplete("diab")
        terms = [t for t, _ in results]
        assert "diabetes" in terms
        assert "diabetes mellitus" in terms
        assert "diabetic neuropathy" in terms

    def test_autocomplete_no_results(self, populated_trie):
        results = populated_trie.autocomplete("xyz")
        assert results == []

    def test_autocomplete_top_k_limits_results(self, populated_trie):
        results = populated_trie.autocomplete("dia", top_k=2)
        assert len(results) <= 2

    def test_autocomplete_returns_all_under_prefix(self, populated_trie):
        results = populated_trie.autocomplete("card")
        terms = [t for t, _ in results]
        assert "cardiac arrest" in terms
        assert "cardiomyopathy" in terms

    def test_autocomplete_with_full_term_prefix(self, populated_trie):
        # "diabetes" is a term AND a prefix for longer terms
        results = populated_trie.autocomplete("diabetes")
        terms = [t for t, _ in results]
        assert "diabetes" in terms
        assert "diabetes mellitus" in terms

    def test_autocomplete_alphabetical_sort(self, populated_trie):
        results = populated_trie.autocomplete("hyp", sort_by="alphabetical")
        terms = [t for t, _ in results]
        assert terms == sorted(terms)

    def test_autocomplete_frequency_sort(self, empty_trie):
        # Insert "hypertension" more times than "hypoglycemia"
        for _ in range(5):
            empty_trie.insert("hypertension")
        empty_trie.insert("hypoglycemia")
        results = empty_trie.autocomplete("hyp", sort_by="frequency")
        assert results[0][0] == "hypertension"
        assert results[0][1] == 5

    def test_autocomplete_single_character_prefix(self, populated_trie):
        results = populated_trie.autocomplete("a")
        terms = [t for t, _ in results]
        assert "asthma" in terms

    def test_autocomplete_returns_tuples(self, populated_trie):
        results = populated_trie.autocomplete("dia")
        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], tuple)
            assert len(results[0]) == 2

    def test_autocomplete_empty_prefix(self, populated_trie):
        # Empty prefix → returns everything (no prefix node = root)
        # _find_node("") returns root
        results = populated_trie.autocomplete("")
        # Should return terms (top_k limited)
        assert len(results) <= 10


# ──────────────────────────────────────────────────────────
# Delete Tests
# ──────────────────────────────────────────────────────────

class TestTrieDelete:
    def test_delete_existing_term(self, populated_trie):
        initial_size = populated_trie.size
        result = populated_trie.delete("diabetes")
        assert result is True
        assert populated_trie.size == initial_size - 1
        assert not populated_trie.search("diabetes")

    def test_delete_nonexistent_term_returns_false(self, populated_trie):
        result = populated_trie.delete("appendicitis")
        assert result is False

    def test_delete_does_not_affect_other_terms(self, populated_trie):
        populated_trie.delete("diabetes")
        # Longer term sharing prefix should still exist
        assert populated_trie.search("diabetes mellitus") is True

    def test_delete_prefix_does_not_remove_extensions(self, empty_trie):
        empty_trie.insert("dia")
        empty_trie.insert("diabetes")
        empty_trie.delete("dia")
        assert not empty_trie.search("dia")
        assert empty_trie.search("diabetes")

    def test_delete_leaf_removes_orphan_nodes(self, empty_trie):
        empty_trie.insert("xyz")
        initial_nodes = empty_trie.node_count
        empty_trie.delete("xyz")
        # Orphan nodes should be pruned
        assert empty_trie.node_count < initial_nodes

    def test_delete_reduces_size(self, empty_trie):
        empty_trie.insert("asthma")
        empty_trie.insert("cancer")
        empty_trie.delete("asthma")
        assert empty_trie.size == 1


# ──────────────────────────────────────────────────────────
# Trie Size & Node Count Tests
# ──────────────────────────────────────────────────────────

class TestTrieMetrics:
    def test_len_operator(self, populated_trie):
        assert len(populated_trie) == populated_trie.size

    def test_initial_size_is_zero(self, empty_trie):
        assert empty_trie.size == 0

    def test_get_all_terms_returns_sorted(self, populated_trie):
        all_terms = populated_trie.get_all_terms()
        assert all_terms == sorted(all_terms)

    def test_get_all_terms_count(self, populated_trie):
        all_terms = populated_trie.get_all_terms()
        assert len(all_terms) == populated_trie.size

    def test_repr(self, populated_trie):
        r = repr(populated_trie)
        assert "Trie(" in r
        assert "terms=" in r


# ──────────────────────────────────────────────────────────
# Edge Case Tests
# ──────────────────────────────────────────────────────────

class TestTrieEdgeCases:
    def test_insert_and_search_numeric_characters(self, empty_trie):
        empty_trie.insert("type 2 diabetes")
        assert empty_trie.search("type 2 diabetes")

    def test_insert_hyphenated_term(self, empty_trie):
        empty_trie.insert("anti-inflammatory")
        assert empty_trie.search("anti-inflammatory")

    def test_large_bulk_insert(self, empty_trie):
        """Verify correct size after bulk insert of 1000 terms."""
        terms = [f"disease{i}" for i in range(1000)]
        for t in terms:
            empty_trie.insert(t)
        assert empty_trie.size == 1000

    def test_autocomplete_after_delete(self, populated_trie):
        populated_trie.delete("diabetes mellitus")
        results = populated_trie.autocomplete("diabetes")
        terms = [t for t, _ in results]
        assert "diabetes mellitus" not in terms
        assert "diabetes" in terms
