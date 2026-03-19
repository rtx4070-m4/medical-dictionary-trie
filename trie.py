"""
trie.py - Core Trie (Prefix Tree) Data Structure

This module implements a highly optimized Trie for medical term storage and retrieval.
Supports O(L) insert/search where L = length of term, with autocomplete in O(L + N)
where N = number of results returned.

Author: Medical Dictionary Trie Project
License: MIT
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class TrieNode:
    """
    Represents a single node in the Trie.

    Each node stores:
    - children: mapping of character → child node
    - is_end: flag indicating a complete word ends here
    - frequency: how many times this term was inserted (for ranking)
    - term: the complete term stored at leaf nodes (avoids DFS reconstruction)
    """
    children: Dict[str, "TrieNode"] = field(default_factory=dict)
    is_end: bool = False
    frequency: int = 0
    term: Optional[str] = None  # Full term stored at end nodes for fast retrieval


class Trie:
    """
    Optimized Trie (Prefix Tree) for fast prefix-based search and autocomplete.

    Time Complexity:
        - Insert:      O(L) where L = length of term
        - Search:      O(L)
        - Autocomplete: O(L + K) where K = number of nodes visited

    Space Complexity:
        - O(A * N) where A = alphabet size, N = number of nodes
    """

    def __init__(self) -> None:
        """Initialize Trie with an empty root node."""
        self.root = TrieNode()
        self._size: int = 0       # Total number of unique terms
        self._node_count: int = 1  # Total nodes (starts at 1 for root)

    # ──────────────────────────────────────────────
    # INSERT
    # ──────────────────────────────────────────────

    def insert(self, term: str) -> bool:
        """
        Insert a term into the Trie.

        Args:
            term: The medical term to insert (should be pre-normalized).

        Returns:
            True if the term was newly inserted, False if it already existed.
        """
        if not term:
            return False

        node = self.root
        for char in term:
            if char not in node.children:
                node.children[char] = TrieNode()
                self._node_count += 1
            node = node.children[char]

        if node.is_end:
            # Term already exists — just increment frequency
            node.frequency += 1
            return False

        # New term — mark end node and store full term
        node.is_end = True
        node.frequency = 1
        node.term = term
        self._size += 1
        return True

    # ──────────────────────────────────────────────
    # SEARCH (exact match)
    # ──────────────────────────────────────────────

    def search(self, term: str) -> bool:
        """
        Check if an exact term exists in the Trie.

        Args:
            term: The term to search for.

        Returns:
            True if the exact term exists, False otherwise.
        """
        node = self._find_node(term)
        return node is not None and node.is_end

    def get_frequency(self, term: str) -> int:
        """
        Return the insertion frequency of a term.

        Args:
            term: The term to look up.

        Returns:
            Frequency count (0 if term not found).
        """
        node = self._find_node(term)
        if node and node.is_end:
            return node.frequency
        return 0

    # ──────────────────────────────────────────────
    # PREFIX CHECK
    # ──────────────────────────────────────────────

    def starts_with(self, prefix: str) -> bool:
        """
        Check if any term in the Trie starts with the given prefix.

        Args:
            prefix: The prefix to check.

        Returns:
            True if at least one term starts with this prefix.
        """
        return self._find_node(prefix) is not None

    # ──────────────────────────────────────────────
    # AUTOCOMPLETE
    # ──────────────────────────────────────────────

    def autocomplete(
        self,
        prefix: str,
        top_k: int = 10,
        sort_by: str = "frequency"
    ) -> List[Tuple[str, int]]:
        """
        Return top-k autocomplete suggestions for a given prefix.

        Performs DFS from the prefix node and collects all complete words,
        then sorts by frequency (descending) or alphabetically.

        Args:
            prefix:   The search prefix.
            top_k:    Maximum number of results to return.
            sort_by:  "frequency" (default) or "alphabetical".

        Returns:
            List of (term, frequency) tuples, sorted by ranking.
        """
        prefix_node = self._find_node(prefix)
        if prefix_node is None:
            return []

        # DFS to collect all words under this prefix node
        results: List[Tuple[str, int]] = []
        self._dfs_collect(prefix_node, results)

        # Sort results based on sort_by strategy
        if sort_by == "frequency":
            results.sort(key=lambda x: (-x[1], x[0]))  # freq desc, alpha asc
        else:
            results.sort(key=lambda x: x[0])  # alphabetical

        return results[:top_k]

    def _dfs_collect(
        self,
        node: TrieNode,
        results: List[Tuple[str, int]]
    ) -> None:
        """
        Internal DFS helper — traverses children and collects complete words.

        Args:
            node:    Current TrieNode being visited.
            results: Accumulator list for (term, frequency) pairs.
        """
        if node.is_end and node.term is not None:
            results.append((node.term, node.frequency))

        for child_node in node.children.values():
            self._dfs_collect(child_node, results)

    # ──────────────────────────────────────────────
    # DELETE
    # ──────────────────────────────────────────────

    def delete(self, term: str) -> bool:
        """
        Remove a term from the Trie.

        Performs post-order cleanup to remove orphan nodes.

        Args:
            term: The term to delete.

        Returns:
            True if term was deleted, False if not found.
        """
        if not self.search(term):
            return False

        self._delete_recursive(self.root, term, 0)
        self._size -= 1
        return True

    def _delete_recursive(
        self,
        node: TrieNode,
        term: str,
        depth: int
    ) -> bool:
        """
        Recursive helper for deletion with orphan-node pruning.

        Returns True if the current node should be deleted (is an orphan).
        """
        if depth == len(term):
            node.is_end = False
            node.frequency = 0
            node.term = None
            return len(node.children) == 0

        char = term[depth]
        if char not in node.children:
            return False

        should_delete_child = self._delete_recursive(
            node.children[char], term, depth + 1
        )

        if should_delete_child:
            del node.children[char]
            self._node_count -= 1
            return not node.is_end and len(node.children) == 0

        return False

    # ──────────────────────────────────────────────
    # UTILITIES
    # ──────────────────────────────────────────────

    def _find_node(self, prefix: str) -> Optional[TrieNode]:
        """
        Traverse the Trie to the node at the end of prefix.

        Args:
            prefix: The prefix to traverse.

        Returns:
            The TrieNode at the end of the prefix, or None if not found.
        """
        node = self.root
        for char in prefix:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def get_all_terms(self) -> List[str]:
        """Return all terms stored in the Trie, sorted alphabetically."""
        results: List[Tuple[str, int]] = []
        self._dfs_collect(self.root, results)
        return sorted(t for t, _ in results)

    @property
    def size(self) -> int:
        """Total number of unique terms in the Trie."""
        return self._size

    @property
    def node_count(self) -> int:
        """Total number of TrieNodes allocated."""
        return self._node_count

    def __len__(self) -> int:
        return self._size

    def __contains__(self, term: str) -> bool:
        return self.search(term)

    def __repr__(self) -> str:
        return (
            f"Trie(terms={self._size}, nodes={self._node_count})"
        )
