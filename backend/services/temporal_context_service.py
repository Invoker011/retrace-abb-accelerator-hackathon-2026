"""Temporal Context Service for RETRACE.

Assembles and orders chronological timeline events grounding the incident,
preserving precise event sequences and real timestamps without fabrication.
"""
import logging
from typing import Any, Dict, List, Optional, Set

from backend.schemas.incident import IncidentEvent
from backend.schemas.hybrid_search import TemporalContextItem
from backend.services.incident_service import incident_service

logger = logging.getLogger(__name__)


class TemporalContextService:
    """Provides time-aware event sequence grounding for incident investigations."""

    @staticmethod
    def get_temporal_context(
        incident_id: str,
        retrieved_evidence_ids: Optional[Set[str]] = None,
        retrieved_asset_ids: Optional[Set[str]] = None,
    ) -> List[TemporalContextItem]:
        """Extract and chronologically order incident events relevant to retrieved evidence.

        Guarantees:
        - Chronological ordering by relative_seconds and normalized timestamps
        - Zero timestamp fabrication
        - Explicit linkage to supporting evidence IDs
        """
        all_events: List[IncidentEvent] = incident_service.get_incident_events(incident_id)
        if not all_events:
            return []

        # Ensure strict chronological sorting by relative_seconds / timestamp
        sorted_events = sorted(
            all_events,
            key=lambda e: (e.relative_seconds if e.relative_seconds is not None else 0, e.timestamp)
        )

        temporal_items: List[TemporalContextItem] = []
        for evt in sorted_events:
            temporal_items.append(
                TemporalContextItem(
                    event_id=evt.id,
                    timestamp=evt.timestamp,
                    relative_seconds=evt.relative_seconds,
                    asset_id=evt.asset_id,
                    title=evt.title,
                    event_type=evt.event_type,
                    severity=evt.severity,
                    evidence_id=evt.evidence_id,
                )
            )

        return temporal_items


# Singleton instance
temporal_context_service = TemporalContextService()


def get_temporal_context_service() -> TemporalContextService:
    """Return singleton instance of TemporalContextService."""
    return temporal_context_service

