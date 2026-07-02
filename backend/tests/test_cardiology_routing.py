import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from backend.graphs.routing_graph import _detect_department
except ImportError:
    from graphs.routing_graph import _detect_department


def test_chest_pain_routes_to_cardiology():
    assert _detect_department("I've been having chest pain since this morning") == "cardiology"


def test_palpitations_routes_to_cardiology():
    assert _detect_department("My heart keeps racing and skipping beats") == "cardiology"


def test_cough_routes_to_general():
    assert _detect_department("I have a bad cough and sore throat") == "general"
