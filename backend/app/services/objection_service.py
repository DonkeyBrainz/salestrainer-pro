"""Objection detection and resolution service for sales coaching.

Uses in-memory keyword matching against curated objection data to detect
customer objections and provide resolution guidance to the coach.
"""

import logging
import re

from app.data.objections import ALL_OBJECTIONS, ObjectionEntry

logger = logging.getLogger(__name__)

# Common stop words to exclude from keyword matching
_STOP_WORDS = frozenset(
    {
        "i",
        "me",
        "my",
        "a",
        "an",
        "the",
        "is",
        "am",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "can",
        "may",
        "might",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "and",
        "but",
        "or",
        "not",
        "no",
        "so",
        "about",
        "just",
        "than",
        "very",
        "too",
        "also",
        "s",
        "t",
        "m",
        "re",
        "ll",
        "ve",
        "d",
    }
)


class ObjectionLookupService:
    """In-memory objection detection using keyword-overlap scoring."""

    def __init__(self) -> None:
        """Initialize with pre-indexed objection keywords."""
        self._objections = ALL_OBJECTIONS
        self._indexed: list[tuple[ObjectionEntry, set[str]]] = []
        for obj in self._objections:
            keywords = self._tokenize(obj["text"])
            self._indexed.append((obj, keywords))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Extract lowercase content-word tokens from text (stop words removed)."""
        words = set(re.findall(r"[a-z]+", text.lower()))
        return words - _STOP_WORDS

    def detect_objection(self, customer_message: str) -> ObjectionEntry | None:
        """Detect if a customer message contains an objection.

        Uses keyword-overlap scoring: counts how many words from each
        known objection text appear in the customer message. Returns
        the best match if it exceeds a minimum threshold.

        Args:
            customer_message: The customer's message text

        Returns:
            Best matching ObjectionEntry, or None if no match
        """
        message_tokens = self._tokenize(customer_message)
        if not message_tokens:
            return None

        best_match: ObjectionEntry | None = None
        best_score = 0.0

        for objection, obj_tokens in self._indexed:
            if not obj_tokens:
                continue
            overlap = len(message_tokens & obj_tokens)
            score = overlap / len(obj_tokens)
            if score > best_score:
                best_score = score
                best_match = objection

        # Require at least 40% keyword overlap to count as a match
        if best_score >= 0.4:
            return best_match
        return None

    def get_resolution_context(self, objection: ObjectionEntry) -> str:
        """Format an objection and its resolution hint for the coach prompt.

        Args:
            objection: The detected objection entry

        Returns:
            Formatted resolution guidance string
        """
        return (
            f"Detected objection ({objection['category'].value}, "
            f"difficulty: {objection['difficulty']}): "
            f'"{objection["text"]}"\n'
            f"Resolution approach: {objection['resolution_hint']}"
        )


# Singleton
_objection_service: ObjectionLookupService | None = None


def get_objection_service() -> ObjectionLookupService:
    """Get objection service singleton.

    Returns:
        ObjectionLookupService instance

    Raises:
        RuntimeError: If service not initialized
    """
    global _objection_service
    if _objection_service is None:
        raise RuntimeError("Objection service not initialized")
    return _objection_service


def init_objection_service() -> None:
    """Initialize objection service singleton."""
    global _objection_service
    _objection_service = ObjectionLookupService()
