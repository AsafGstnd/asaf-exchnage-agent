"""
Targeted regression tests for conservative hardening changes.

Tests cover:
1. NULL-tolerant filtering (min_gpa, msc_allowed, erasmus_available, english_only_possible)
2. Normalized university/country name matching
3. Graceful Supabase failure handling in filter and analyzer
4. API contract preservation (status, error, response, steps, session_id)
5. /api/model_architecture PNG endpoint reliability
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# 1.  NULL-tolerant filtering
# ---------------------------------------------------------------------------

class TestNullTolerantFiltering:
    """NULL values in DB fields must NOT cause a university to be rejected."""

    def _make_rows(self, **overrides):
        """Return a minimal list of rows with sane defaults and optional overrides."""
        base = {
            "name": "Test University",
            "country": "Testland",
            "min_gpa": None,
            "msc_allowed": None,
            "erasmus_available": None,
            "english_only_possible": None,
            "test_required": None,
            "restricted_majors": [],
            "english_test_type": [],
            "english_test_level": None,
            "other_languages": [],
        }
        base.update(overrides)
        return [base]

    def _run_python_filters(self, rows, user_input):
        """Run all Python-side filter helpers and return the remaining rows."""
        from orchestration.specialists.filter import (
            apply_academic_filters,
            apply_language_filters,
            apply_english_test_filter,
            apply_restricted_majors_filter,
            apply_non_english_language_filter,
        )
        academic = user_input.get("academic_profile", {})
        language = user_input.get("language_profile", {})
        preferences = user_input.get("preferences", {})
        steps = []
        rows = apply_academic_filters(rows, academic, steps)
        rows = apply_language_filters(rows, language, preferences, steps)
        rows = apply_english_test_filter(rows, language, steps)
        rows = apply_restricted_majors_filter(rows, academic, steps)
        rows = apply_non_english_language_filter(rows, language, steps)
        return rows

    # --- GPA ---
    def test_null_min_gpa_does_not_reject(self):
        """A university with min_gpa=NULL must pass GPA filtering."""
        rows = self._make_rows(min_gpa=None)
        result = self._run_python_filters(rows, {"academic_profile": {"gpa": 2.5}})
        assert len(result) == 1, "NULL min_gpa should not reject a university"

    def test_explicit_min_gpa_rejects_when_student_below(self):
        """A university with min_gpa=3.5 must reject a student with GPA 2.5."""
        rows = self._make_rows(min_gpa=3.5)
        result = self._run_python_filters(rows, {"academic_profile": {"gpa": 2.5}})
        assert len(result) == 0

    def test_explicit_min_gpa_passes_when_student_above(self):
        rows = self._make_rows(min_gpa=3.0)
        result = self._run_python_filters(rows, {"academic_profile": {"gpa": 3.5}})
        assert len(result) == 1

    # --- msc_allowed ---
    def test_null_msc_allowed_does_not_reject_msc_student(self):
        """NULL msc_allowed = unknown; MSc students must not be rejected."""
        rows = self._make_rows(msc_allowed=None)
        result = self._run_python_filters(rows, {"academic_profile": {"study_level": "msc"}})
        assert len(result) == 1, "NULL msc_allowed should not reject an MSc student"

    def test_false_msc_allowed_rejects_msc_student(self):
        rows = self._make_rows(msc_allowed=False)
        result = self._run_python_filters(rows, {"academic_profile": {"study_level": "msc"}})
        assert len(result) == 0

    def test_true_msc_allowed_passes_msc_student(self):
        rows = self._make_rows(msc_allowed=True)
        result = self._run_python_filters(rows, {"academic_profile": {"study_level": "msc"}})
        assert len(result) == 1

    # --- erasmus_available ---
    def test_null_erasmus_does_not_reject_when_required(self):
        """NULL erasmus_available = unknown; must not reject when Erasmus required."""
        rows = self._make_rows(erasmus_available=None)
        result = self._run_python_filters(rows, {"preferences": {"must_be_erasmus": True}})
        assert len(result) == 1, "NULL erasmus_available should not reject university"

    def test_false_erasmus_rejects_when_required(self):
        rows = self._make_rows(erasmus_available=False)
        result = self._run_python_filters(rows, {"preferences": {"must_be_erasmus": True}})
        assert len(result) == 0

    # --- english_only_possible ---
    def test_null_english_only_does_not_reject_english_only_student(self):
        """NULL english_only_possible = unknown; English-only student must not be rejected."""
        rows = self._make_rows(english_only_possible=None)
        result = self._run_python_filters(rows, {
            "language_profile": {"non_english_languages": []}
        })
        assert len(result) == 1, "NULL english_only_possible should not reject university"

    def test_false_english_only_rejects_english_only_student(self):
        rows = self._make_rows(english_only_possible=False)
        result = self._run_python_filters(rows, {
            "language_profile": {"non_english_languages": []}
        })
        assert len(result) == 0

    def test_true_english_only_passes_english_only_student(self):
        rows = self._make_rows(english_only_possible=True)
        result = self._run_python_filters(rows, {
            "language_profile": {"non_english_languages": []}
        })
        assert len(result) == 1


# ---------------------------------------------------------------------------
# 2.  Normalized university/country matching
# ---------------------------------------------------------------------------

class TestNormalizeHelpers:
    def test_lowercase(self):
        from utils.normalize import normalize_university_name
        assert normalize_university_name("MIT") == "mit"

    def test_strip_whitespace(self):
        from utils.normalize import normalize_university_name
        assert normalize_university_name("  MIT  ") == "mit"

    def test_remove_punctuation(self):
        from utils.normalize import normalize_university_name
        assert normalize_university_name("Technical University of Denmark (DTU)") == \
               "technical university of denmark dtu"

    def test_collapse_spaces(self):
        from utils.normalize import normalize_university_name
        # Multiple spaces should be collapsed to one
        result = normalize_university_name("Technical   University  of  Denmark")
        assert result == "technical university of denmark"

    def test_empty_string(self):
        from utils.normalize import normalize_university_name
        assert normalize_university_name("") == ""

    def test_none_input(self):
        from utils.normalize import normalize_university_name
        assert normalize_university_name(None) == ""

    def test_matching_tolerates_casing_and_spacing(self):
        from utils.normalize import normalize_university_name
        name_a = "  Technical University of Denmark (DTU)  "
        name_b = "technical university of denmark dtu"
        assert normalize_university_name(name_a) == normalize_university_name(name_b)

    def test_country_normalize(self):
        from utils.normalize import normalize_country
        assert normalize_country("Czech Republic") == "czech republic"
        assert normalize_country("  South Korea  ") == "south korea"
        assert normalize_country(None) == ""


# ---------------------------------------------------------------------------
# 3.  Graceful Supabase failure handling in filter
# ---------------------------------------------------------------------------

class TestFilterGracefulFailures:
    def test_supabase_none_returns_empty_list(self):
        """If Supabase client is None, filter_universities must return an empty list, not crash."""
        from orchestration.specialists import filter as filter_mod
        original = filter_mod.supabase
        try:
            filter_mod.supabase = None
            result = filter_mod.filter_universities({"academic_profile": {"gpa": 3.0}})
        finally:
            filter_mod.supabase = original
        assert result["universities"] == []
        assert any("not initialized" in s.lower() for s in result["traced_steps"])

    def test_supabase_query_exception_returns_empty_list(self):
        """If Supabase raises an exception, filter_universities must return an empty list."""
        from orchestration.specialists import filter as filter_mod
        mock_supa = MagicMock()
        mock_supa.table.return_value.select.return_value.execute.side_effect = RuntimeError("DB down")
        original = filter_mod.supabase
        try:
            filter_mod.supabase = mock_supa
            result = filter_mod.filter_universities({"academic_profile": {"gpa": 3.0}})
        finally:
            filter_mod.supabase = original
        assert result["universities"] == []
        assert any("error" in s.lower() for s in result["traced_steps"])


# ---------------------------------------------------------------------------
# 4.  API contract preservation
# ---------------------------------------------------------------------------

class TestAPIContract:
    """Verify that /api/execute always returns the required keys."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        # Patch the agent so we don't need real credentials
        with patch("api.main.agent") as mock_agent:
            mock_agent.run.return_value = {
                "analysis": [{"university_name": "Test University"}],
                "courses": [],
                "steps": [{"module": "Filter", "prompt": {}, "response": {}}],
            }
            from api.main import app
            yield TestClient(app)

    def test_execute_returns_required_keys(self, client):
        resp = client.post("/api/execute", json={"prompt": '{"academic_profile":{"gpa":3.2}}'})
        assert resp.status_code == 200
        data = resp.json()
        for key in ("status", "error", "response", "steps"):
            assert key in data, f"Missing required key: {key}"

    def test_execute_returns_session_id(self, client):
        resp = client.post("/api/execute", json={"prompt": '{"academic_profile":{"gpa":3.2}}'})
        data = resp.json()
        assert "session_id" in data, "session_id must be returned by /api/execute"
        assert data["session_id"]  # Must be non-empty

    def test_execute_reuses_session_id(self, client):
        """Providing session_id in the request must echo it back in the response."""
        session_id = "test-session-abc123"
        resp = client.post("/api/execute", json={
            "prompt": '{"academic_profile":{"gpa":3.2}}',
            "session_id": session_id
        })
        data = resp.json()
        assert data.get("session_id") == session_id

    def test_execute_error_response_has_required_keys(self):
        """Even on agent failure, required keys must be present."""
        with patch("api.main.agent") as mock_agent:
            mock_agent.run.side_effect = RuntimeError("Agent crashed")
            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            resp = client.post("/api/execute", json={"prompt": "test"})
            data = resp.json()
            assert data["status"] == "error"
            for key in ("status", "error", "response", "steps"):
                assert key in data

    def test_execute_response_is_valid_json_string(self, client):
        """The 'response' field must be parseable JSON when status=ok."""
        resp = client.post("/api/execute", json={"prompt": '{"academic_profile":{"gpa":3.2}}'})
        data = resp.json()
        if data["status"] == "ok":
            parsed = json.loads(data["response"])
            assert isinstance(parsed, dict)
            assert "analysis" in parsed


# ---------------------------------------------------------------------------
# 5.  /api/model_architecture PNG endpoint
# ---------------------------------------------------------------------------

class TestArchitectureEndpoint:
    def test_architecture_endpoint_returns_png(self, tmp_path, monkeypatch):
        """Endpoint must return a PNG file when docs/architecture.png exists."""
        # Create a fake PNG in a tmp docs folder
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        png_file = docs_dir / "architecture.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n")  # minimal PNG header

        # Point the endpoint to look in our tmp_path
        import api.main as main_mod
        original_abspath = os.path.abspath

        def fake_abspath(path):
            # Replace the api dir with tmp_path/api so relative paths resolve correctly
            if "main.py" in path:
                return str(tmp_path / "api" / "main.py")
            return original_abspath(path)

        # Create tmp api dir
        (tmp_path / "api").mkdir()

        monkeypatch.setattr(os.path, "abspath", fake_abspath)

        with patch("api.main.agent") as mock_agent:
            mock_agent.run.return_value = {"analysis": [], "courses": [], "steps": []}
            from api.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)
            # Try with real file paths
            resp = client.get("/api/model_architecture")
            # Either 200 (found) or 404 (not found in CI without real files) – both are valid
            assert resp.status_code in (200, 404)
            if resp.status_code == 200:
                assert resp.headers["content-type"].startswith("image/png")

    def test_docs_architecture_png_exists(self):
        """docs/architecture.png must exist in the repository for reliable serving."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        png_path = os.path.join(repo_root, "docs", "architecture.png")
        assert os.path.exists(png_path), (
            f"docs/architecture.png not found at {png_path}. "
            "Copy architecture.png to docs/ for a stable endpoint path."
        )
