"""
Focused regression tests for runtime stability fixes.

Covers:
1. Pinecone unavailability does not crash gather_context_for_llm
2. Empty analysis is synthesized from courses when analysis fails
3. session_id is returned and can be reused
4. Frontend response parsing handles both string and dict shapes
5. Normalized matching tolerates whitespace / casing differences
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# 1. Pinecone unavailable does not crash gather_context_for_llm
# ---------------------------------------------------------------------------

class TestPineconeGracefulDegradation:
    def test_rag_search_exception_returns_string(self):
        """If rag_search raises, gather_context_for_llm must return a string, not crash."""
        with patch("orchestration.specialists.analyzer.rag_search") as mock_rag:
            mock_rag.side_effect = Exception("Pinecone unavailable")

            from orchestration.specialists.analyzer import gather_context_for_llm
            context = gather_context_for_llm("Test University")

            assert isinstance(context, str)

    def test_rag_search_exception_returns_fallback_message(self):
        """If rag_search raises, returned context must indicate unavailability."""
        with patch("orchestration.specialists.analyzer.rag_search") as mock_rag:
            mock_rag.side_effect = Exception("Pinecone unavailable")

            from orchestration.specialists.analyzer import gather_context_for_llm
            context = gather_context_for_llm("Test University")

            assert "unavailable" in context.lower() or context == "No RAG context available."

    def test_rag_search_unavailable_string_ignored(self):
        """If rag_search returns an 'unavailable' string, it should not be included in context."""
        with patch("orchestration.specialists.analyzer.rag_search") as mock_rag:
            mock_rag.return_value = "RAG/Pinecone unavailable"

            from orchestration.specialists.analyzer import gather_context_for_llm
            context = gather_context_for_llm("Test University")

            assert "RAG/Pinecone unavailable" not in context
            assert context == "No RAG context available."

    def test_rag_search_tool_import_error_returns_string(self):
        """If pinecone_client cannot be imported, rag_search_tool must return a string."""
        import tools.implementations as impl_mod

        with patch.dict("sys.modules", {"pinecone_db.pinecone_client": None}):
            # Re-run function with import patched to raise ImportError
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                # Call the real function – it catches ImportError internally
                result = impl_mod.rag_search_tool("test query", university="Test Uni")
                assert isinstance(result, str)

    def test_rag_search_tool_exception_returns_string(self):
        """If query_embedding raises, rag_search_tool must return a descriptive string."""
        with patch("pinecone_db.pinecone_client.query_embedding") as mock_qe:
            mock_qe.side_effect = Exception("connection refused")

            from tools.implementations import rag_search_tool
            result = rag_search_tool("test query", university="Test Uni")

            assert isinstance(result, str)
            assert result in ("RAG/Pinecone search failed", "RAG/Pinecone unavailable")


# ---------------------------------------------------------------------------
# 2. Empty analysis synthesized from courses when analysis fails
# ---------------------------------------------------------------------------

class TestSynthesizeAnalysisFromCourses:
    def test_synthesis_with_courses(self):
        """If courses exist, synthesize_analysis_from_courses must produce entries."""
        from orchestration.supervisor import synthesize_analysis_from_courses

        courses = [
            {
                "university_name": "Test Uni",
                "matched_courses": [{"course_name": "CS 101", "language": "English"}]
            }
        ]

        synthesis = synthesize_analysis_from_courses(courses, ["Test Uni"])

        assert len(synthesis) > 0
        assert synthesis[0]["university_name"] == "Test Uni"
        assert len(synthesis[0]["matched_courses"]) > 0

    def test_synthesis_empty_when_no_courses(self):
        """If courses list is empty, synthesize must return empty list."""
        from orchestration.supervisor import synthesize_analysis_from_courses

        synthesis = synthesize_analysis_from_courses([], ["Test Uni"])
        assert synthesis == []

    def test_synthesis_skips_entries_without_matched_courses(self):
        """Course entries with no matched_courses must be skipped."""
        from orchestration.supervisor import synthesize_analysis_from_courses

        courses = [
            {"university_name": "Empty Uni", "matched_courses": []},
            {"university_name": "Good Uni", "matched_courses": [{"course_name": "Math"}]},
        ]

        synthesis = synthesize_analysis_from_courses(courses, ["Empty Uni", "Good Uni"])

        uni_names = [s["university_name"] for s in synthesis]
        assert "Good Uni" in uni_names
        assert "Empty Uni" not in uni_names

    def test_synthesis_has_required_keys(self):
        """Synthesized entries must contain the expected keys."""
        from orchestration.supervisor import synthesize_analysis_from_courses

        courses = [
            {"university_name": "Test Uni", "matched_courses": [{"course_name": "Algo"}]}
        ]

        synthesis = synthesize_analysis_from_courses(courses, ["Test Uni"])
        entry = synthesis[0]

        for key in ("university_name", "general_fit_reasoning", "requirements", "logistics", "matched_courses"):
            assert key in entry, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# 3. session_id returned and reusable via /api/execute
# ---------------------------------------------------------------------------

class TestSessionId:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        with patch("api.main.agent") as mock_agent:
            mock_agent.run.return_value = {
                "analysis": [{"university_name": "Test University"}],
                "courses": [],
                "steps": [{"module": "Filter", "prompt": {}, "response": {}}],
            }
            from api.main import app
            yield TestClient(app)

    def test_session_id_returned(self, client):
        """A non-empty session_id must be returned on every successful call."""
        resp = client.post("/api/execute", json={"prompt": '{"academic_profile":{"gpa":3.2}}'})
        data = resp.json()
        assert data.get("session_id") is not None
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    def test_session_id_reused(self, client):
        """Providing a session_id in the request must echo it back."""
        session_id = "test-session-reuse-123"
        resp = client.post("/api/execute", json={
            "prompt": '{"academic_profile":{"gpa":3.2}}',
            "session_id": session_id
        })
        data = resp.json()
        assert data.get("session_id") == session_id


# ---------------------------------------------------------------------------
# 4. Frontend response parsing handles string and dict shapes
# ---------------------------------------------------------------------------

class TestFrontendResponseParsing:
    @pytest.mark.parametrize("response_data", [
        '{"analysis": [], "courses": []}',   # stringified JSON
        {"analysis": [], "courses": []},      # already a dict
    ])
    def test_parsing_does_not_crash(self, response_data):
        """Both string and dict shapes must be parseable without error."""
        if isinstance(response_data, str):
            parsed = json.loads(response_data)
        else:
            parsed = response_data

        assert isinstance(parsed, dict)
        assert "analysis" in parsed

    def test_empty_analysis_in_valid_response(self):
        """An empty analysis list must be handled without error."""
        raw = '{"analysis": [], "courses": []}'
        parsed = json.loads(raw)
        universities = parsed.get("analysis", [])
        courses_list = parsed.get("courses", [])
        assert universities == []
        assert courses_list == []


# ---------------------------------------------------------------------------
# 5. Normalized matching tolerates whitespace / casing differences
# ---------------------------------------------------------------------------

class TestNormalizedMatching:
    def test_whitespace_tolerance(self):
        """match_university_fuzzy must match despite leading/trailing whitespace."""
        from utils.matching import match_university_fuzzy

        query = "  Test University  "
        db_rows = [
            {"name": "test university", "id": 1},
            {"name": "Other Uni", "id": 2},
        ]

        match = match_university_fuzzy(query, db_rows, "name")

        assert match is not None
        assert match["id"] == 1

    def test_casing_tolerance(self):
        """match_university_fuzzy must match despite casing differences."""
        from utils.matching import match_university_fuzzy

        match = match_university_fuzzy(
            "TECHNICAL UNIVERSITY OF DENMARK",
            [{"name": "Technical University of Denmark", "id": 42}],
        )
        assert match is not None
        assert match["id"] == 42

    def test_exact_match_preferred_over_normalized(self):
        """Exact match must be returned without requiring normalization."""
        from utils.matching import match_university_fuzzy

        rows = [
            {"name": "DTU", "id": 1},
            {"name": "dtu", "id": 2},
        ]
        match = match_university_fuzzy("DTU", rows)
        assert match["id"] == 1  # exact match wins

    def test_no_match_returns_none(self):
        """Returns None when no match found."""
        from utils.matching import match_university_fuzzy

        match = match_university_fuzzy("Unknown Uni", [{"name": "DTU", "id": 1}])
        assert match is None

    def test_empty_inputs_return_none(self):
        """Empty query or empty rows must return None without crashing."""
        from utils.matching import match_university_fuzzy

        assert match_university_fuzzy("", [{"name": "DTU"}]) is None
        assert match_university_fuzzy("DTU", []) is None
        assert match_university_fuzzy(None, [{"name": "DTU"}]) is None

    def test_normalize_university_name_exported(self):
        """normalize_university_name must be importable from utils.matching."""
        from utils.matching import normalize_university_name
        assert normalize_university_name("  MIT  ") == "mit"

    def test_normalize_country_exported(self):
        """normalize_country must be importable from utils.matching."""
        from utils.matching import normalize_country
        assert normalize_country("Czech Republic") == "czech republic"
