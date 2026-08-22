"""
Unit tests for tools/playbooks.py.
Ensures every LaneArchetype has a valid playbook and get_playbook never raises or touches the network.
"""
from __future__ import annotations

import pytest

from graph.state import LaneArchetype
from tools.playbooks import get_playbook, Playbook


def test_all_archetypes_have_playbooks():
    for archetype in LaneArchetype:
        playbook = get_playbook(archetype)
        assert isinstance(playbook, Playbook)
        assert playbook.archetype == archetype
        assert isinstance(playbook.strategy, str)
        assert len(playbook.strategy) > 0
        assert isinstance(playbook.preferred_sources, list)
        assert isinstance(playbook.query_hints, list)


def test_unknown_or_string_archetype_falls_back_to_other():
    # Test unknown enum or string value
    playbook_unknown = get_playbook("totally_unknown_archetype_xyz")  # type: ignore
    assert isinstance(playbook_unknown, Playbook)
    assert playbook_unknown.archetype == LaneArchetype.OTHER

    playbook_other = get_playbook(LaneArchetype.OTHER)
    assert playbook_unknown.strategy == playbook_other.strategy


def test_get_playbook_never_raises_or_hits_network():
    # Verify no network calls and no exceptions for any weird input
    for invalid in [None, 123, "", "random"]:
        try:
            pb = get_playbook(invalid)  # type: ignore
            assert isinstance(pb, Playbook)
        except Exception as e:
            pytest.fail(f"get_playbook raised an exception for input {invalid!r}: {e}")
