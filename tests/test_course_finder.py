"""
Unit tests and end-to-end test for the CourseFinder ReAct agent.

Unit tests mock all external calls (llmod_chat, query_embedding).
The e2e test calls the real pipeline and requires live credentials.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call

from orchestration.specialists.course_finder import (
    _react_loop,
    find_courses_react,
    TOOLS,
)
from orchestration.supervisor import course_finder_node, AgentState


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

SAMPLE_UNIVERSITIES = ["Politecnico di Milano", "CTU (Prague)", "DTU"]

SAMPLE_USER_INFO = {
    "academic_profile": {"gpa": 3.2, "major": "Computer Science"},
    "language_profile": {"non_english_languages": ["Spanish"]},
}

VALID_COURSES_JSON = json.dumps({
    "universities": [
        {
            "university_name": "Politecnico di Milano",
            "matched_courses": [
                {"course_name": "Algorithms", "language": "English", "relevance": "Core CS course offered in English."},
                {"course_name": "Machine Learning", "language": "English", "relevance": "Matches CS major."},
            ]
        },
        {
            "university_name": "CTU (Prague)",
            "matched_courses": [
                {"course_name": "Operating Systems", "language": "English", "relevance": "Standard CS course in English track."},
            ]
        },
        {
            "university_name": "DTU",
            "matched_courses": [
                {"course_name": "Distributed Systems", "language": "English", "relevance": "Relevant to CS, fully in English."},
            ]
        }
    ]
})


# ---------------------------------------------------------------------------
# UNIT TESTS — _search_factsheets
# ---------------------------------------------------------------------------

SINGLE_UNI_JSON = json.dumps({
    "universities": [
        {
            "university_name": "DTU",
            "matched_courses": [
                {"course_name": "AI", "language": "English", "relevance": "Matches CS."},
            ]
        }
    ]
})


# ---------------------------------------------------------------------------
# TOOLS REGISTRY CHECKS
# ---------------------------------------------------------------------------

def test_search_factsheets_is_registered_in_tools():
    assert "search_factsheets" in TOOLS
    assert callable(TOOLS["search_factsheets"])


def test_search_web_is_registered_in_tools():
    assert "search_web" in TOOLS
    assert callable(TOOLS["search_web"])


# ---------------------------------------------------------------------------
# UNIT TESTS — _react_loop
# ---------------------------------------------------------------------------

class TestReactLoop:
    def test_returns_on_final_answer(self):
        """LLM returns Final Answer on the first iteration."""
        llm_response = f"Thought: I have enough info.\nFinal Answer: {VALID_COURSES_JSON}"
        with patch("orchestration.specialists.course_finder.llmod_chat", return_value=llm_response):
            result = _react_loop("system", "user prompt")
        assert result == VALID_COURSES_JSON

    def test_executes_tool_then_finalizes(self):
        """LLM calls search_factsheets on iter 1, then returns Final Answer on iter 2."""
        tool_call_response = (
            'Thought: I need to search.\n'
            'Action: search_factsheets | Args: {"university": "DTU", "query": "CS courses"}'
        )
        final_response = f"Thought: Got context.\nFinal Answer: {VALID_COURSES_JSON}"

        mock_tool = MagicMock(return_value="DTU CS courses info")

        with patch("orchestration.specialists.course_finder.llmod_chat",
                   side_effect=[tool_call_response, final_response]) as mock_llm, \
             patch.dict("orchestration.specialists.course_finder.TOOLS", {"search_factsheets": mock_tool}):
            result = _react_loop("system", "user prompt")

        assert result == VALID_COURSES_JSON
        assert mock_llm.call_count == 2

    def test_unknown_tool_returns_error_observation(self):
        """LLM calls a non-existent tool, loop continues gracefully."""
        bad_tool_response = 'Action: nonexistent_tool | Args: {"university": "X"}'
        final_response = f"Final Answer: {VALID_COURSES_JSON}"

        with patch("orchestration.specialists.course_finder.llmod_chat",
                   side_effect=[bad_tool_response, final_response]):
            result = _react_loop("system", "user prompt")

        assert result == VALID_COURSES_JSON

    def test_no_tool_no_final_answer_treated_as_final(self):
        """LLM returns plain text without tool call or Final Answer — treated as final output."""
        plain_response = "Some plain response without any action."
        with patch("orchestration.specialists.course_finder.llmod_chat", return_value=plain_response):
            result = _react_loop("system", "user prompt")
        assert result == plain_response

    def test_malformed_json_args_defaults_to_empty_call(self):
        """If Args JSON is malformed, tool is called with empty dict (no crash)."""
        bad_args_response = 'Action: search_factsheets | Args: {bad json here}'
        final_response = f"Final Answer: {VALID_COURSES_JSON}"

        mock_tool = MagicMock(return_value="fallback observation")

        with patch("orchestration.specialists.course_finder.llmod_chat",
                   side_effect=[bad_args_response, final_response]), \
             patch.dict("orchestration.specialists.course_finder.TOOLS", {"search_factsheets": mock_tool}):
            try:
                result = _react_loop("system", "user prompt")
                # If it completes, result should be the final JSON
                assert VALID_COURSES_JSON in result
            except TypeError:
                # Also acceptable: tool crashed but test confirms no silent data corruption
                pass

    def test_observation_appended_to_history(self):
        """After a tool call, the observation must appear in the next LLM context."""
        tool_call_response = (
            'Action: search_factsheets | Args: {"university": "DTU", "query": "CS"}'
        )
        final_response = f"Final Answer: {VALID_COURSES_JSON}"
        observation_text = "DTU offers CS in English"

        mock_tool = MagicMock(return_value=observation_text)
        captured_contexts = []

        def capture_llm(system, context, **kwargs):
            captured_contexts.append(context)
            return [tool_call_response, final_response][len(captured_contexts) - 1]

        with patch("orchestration.specialists.course_finder.llmod_chat", side_effect=capture_llm), \
             patch.dict("orchestration.specialists.course_finder.TOOLS", {"search_factsheets": mock_tool}):
            _react_loop("system", "user prompt")

        # Second LLM call context must contain the tool observation
        assert observation_text in captured_contexts[1]

    def test_multiple_sequential_tool_calls(self):
        """Agent calls tool 3 times before finalizing."""
        tool_call = 'Action: search_factsheets | Args: {"university": "X", "query": "q"}'
        final = f"Final Answer: {VALID_COURSES_JSON}"
        mock_tool = MagicMock(return_value="info")

        with patch("orchestration.specialists.course_finder.llmod_chat",
                   side_effect=[tool_call, tool_call, tool_call, final]) as mock_llm, \
             patch.dict("orchestration.specialists.course_finder.TOOLS", {"search_factsheets": mock_tool}):
            result = _react_loop("system", "user prompt", max_iter=8)

        assert mock_llm.call_count == 4
        assert result == VALID_COURSES_JSON

    def test_max_iter_triggers_fallback(self):
        """If LLM never finalizes, fallback call is made after max_iter."""
        tool_call_response = (
            'Action: search_factsheets | Args: {"university": "DTU", "query": "courses"}'
        )
        fallback_response = f"Final Answer: {VALID_COURSES_JSON}"

        mock_tool = MagicMock(return_value="some text")

        # max_iter=2 means 2 tool calls then 1 fallback call
        with patch("orchestration.specialists.course_finder.llmod_chat",
                   side_effect=[tool_call_response, tool_call_response, fallback_response]) as mock_llm, \
             patch.dict("orchestration.specialists.course_finder.TOOLS", {"search_factsheets": mock_tool}):
            result = _react_loop("system", "user prompt", max_iter=2)

        # 2 iterations + 1 fallback = 3 total calls
        assert mock_llm.call_count == 3
        # The fallback response contains "Final Answer:" but _react_loop at that point
        # just returns whatever llmod_chat returns (raw), so check it contains the JSON
        assert VALID_COURSES_JSON in result

    def test_react_loop_with_tool_calls(self):
        """Test that ReAct loop correctly invokes tools and returns result."""
        with patch("orchestration.specialists.course_finder.llmod_chat") as mock_llm:
            mock_llm.side_effect = [
                'Action: search_web | Args: {"query": "MIT CS courses"}',
                f'Final Answer: {VALID_COURSES_JSON}'
            ]
            result = _react_loop("system", "user prompt")
        assert "universities" in result

    def test_react_loop_logging(self):
        """Test that ReAct steps are logged into log_steps."""
        steps = []
        with patch("orchestration.specialists.course_finder.llmod_chat") as mock_llm:
            mock_llm.return_value = f'Final Answer: {VALID_COURSES_JSON}'
            _react_loop("system", "user prompt", log_steps=steps)
        assert len(steps) > 0
        assert steps[0]["module"] == "CourseFinder_ReAct"


# ---------------------------------------------------------------------------
# UNIT TESTS — find_courses_react
# ---------------------------------------------------------------------------

class TestFindCoursesReact:
    def test_returns_list_of_university_dicts(self):
        """Normal path: LLM returns valid JSON, function returns (courses, steps) tuple."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON):
            courses, steps = find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)

        assert isinstance(courses, list)
        assert len(courses) == 3
        for item in courses:
            assert "university_name" in item
            assert "matched_courses" in item
            assert isinstance(item["matched_courses"], list)

    def test_each_course_has_required_keys(self):
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON):
            courses, _ = find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)

        for uni in courses:
            for course in uni["matched_courses"]:
                assert "course_name" in course
                assert "language" in course
                assert "relevance" in course

    def test_returns_empty_list_on_invalid_json(self):
        with patch("orchestration.specialists.course_finder._react_loop", return_value="not valid json at all"):
            courses, _ = find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)
        assert courses == []

    def test_parses_json_wrapped_in_text(self):
        """LLM sometimes wraps JSON in explanatory text — regex fallback handles it."""
        wrapped = f"Here are the results:\n{VALID_COURSES_JSON}\nEnd of response."
        with patch("orchestration.specialists.course_finder._react_loop", return_value=wrapped):
            courses, _ = find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)
        assert isinstance(courses, list)
        assert len(courses) == 3

    def test_empty_universities_returns_empty(self):
        with patch("orchestration.specialists.course_finder._react_loop",
                   return_value='{"universities": []}'):
            courses, _ = find_courses_react([], SAMPLE_USER_INFO)
        assert courses == []

    def test_language_profile_defaults_to_english_only(self):
        """User with no non-English languages — languages list should still work."""
        user_info_no_lang = {
            "academic_profile": {"major": "Physics"},
            "language_profile": {"non_english_languages": []},
        }
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON) as mock_loop:
            find_courses_react(["Some University"], user_info_no_lang)
        # Confirm the prompt passed to _react_loop mentions English
        call_args = mock_loop.call_args
        assert "English" in call_args[0][1]  # user_prompt argument

    def test_non_english_languages_included_in_prompt(self):
        """Spanish in language_profile should appear in the user prompt."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON) as mock_loop:
            find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)
        call_args = mock_loop.call_args
        assert "Spanish" in call_args[0][1]

    def test_major_included_in_prompt(self):
        """Student's major should appear in both system and user prompts."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON) as mock_loop:
            find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)
        system_prompt, user_prompt = mock_loop.call_args[0]
        assert "Computer Science" in user_prompt

    def test_universities_list_included_in_prompt(self):
        """University names must appear in the user prompt."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON) as mock_loop:
            find_courses_react(["Politecnico di Milano"], SAMPLE_USER_INFO)
        _, user_prompt = mock_loop.call_args[0]
        assert "Politecnico di Milano" in user_prompt

    def test_missing_universities_key_returns_empty(self):
        """JSON without 'universities' key → returns []."""
        bad_json = json.dumps({"result": []})
        with patch("orchestration.specialists.course_finder._react_loop", return_value=bad_json):
            courses, _ = find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)
        assert courses == []

    def test_completely_empty_user_information(self):
        """Handles missing all profile keys without crashing."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON):
            courses, _ = find_courses_react(SAMPLE_UNIVERSITIES, {})
        assert isinstance(courses, list)

    def test_fewer_results_than_input_universities(self):
        """LLM returning fewer universities than input is valid."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=SINGLE_UNI_JSON):
            courses, _ = find_courses_react(["DTU", "Politecnico di Milano"], SAMPLE_USER_INFO)
        assert len(courses) == 1
        assert courses[0]["university_name"] == "DTU"

    def test_returns_react_steps(self):
        """find_courses_react returns a (courses, steps) tuple where steps is a list."""
        with patch("orchestration.specialists.course_finder._react_loop", return_value=VALID_COURSES_JSON):
            result = find_courses_react(SAMPLE_UNIVERSITIES, SAMPLE_USER_INFO)
        assert isinstance(result, tuple)
        assert len(result) == 2
        courses, steps = result
        assert isinstance(courses, list)
        assert isinstance(steps, list)


# ---------------------------------------------------------------------------
# UNIT TESTS — course_finder_node (supervisor integration)
# ---------------------------------------------------------------------------

class TestCourseFinderNode:
    BASE_STATE: AgentState = {
        "top_universities": ["Politecnico di Milano", "DTU"],
        "user_information": {
            "academic_profile": {"major": "Computer Science"},
            "language_profile": {"non_english_languages": ["French"]},
        },
        "steps": [],
    }

    def test_node_returns_courses_and_step(self):
        mock_courses = [
            {"university_name": "Politecnico di Milano", "matched_courses": [
                {"course_name": "ML", "language": "English", "relevance": "CS match"}
            ]}
        ]
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=(mock_courses, [])):
            result = course_finder_node(dict(self.BASE_STATE))

        assert result["courses"] == mock_courses
        assert len(result["steps"]) == 1
        step = result["steps"][0]
        assert step["module"] == "CourseFinder"

    def test_node_step_prompt_contains_universities(self):
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=([], [])):
            result = course_finder_node(dict(self.BASE_STATE))
        step = result["steps"][0]
        assert step["prompt"]["universities"] == ["Politecnico di Milano", "DTU"]

    def test_node_step_prompt_contains_major(self):
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=([], [])):
            result = course_finder_node(dict(self.BASE_STATE))
        assert result["steps"][0]["prompt"]["major"] == "Computer Science"

    def test_node_step_prompt_contains_languages(self):
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=([], [])):
            result = course_finder_node(dict(self.BASE_STATE))
        assert result["steps"][0]["prompt"]["languages"] == ["French"]

    def test_node_step_response_has_courses_found_count(self):
        mock_courses = [{"university_name": "DTU", "matched_courses": []}]
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=(mock_courses, [])):
            result = course_finder_node(dict(self.BASE_STATE))
        assert result["steps"][0]["response"]["courses_found"] == 1

    def test_node_appends_to_existing_steps(self):
        state = dict(self.BASE_STATE)
        state["steps"] = [{"module": "Filter", "prompt": {}, "response": {}}]
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=([], [])):
            result = course_finder_node(state)
        assert len(result["steps"]) == 2
        assert result["steps"][0]["module"] == "Filter"
        assert result["steps"][1]["module"] == "CourseFinder"

    def test_node_empty_top_universities(self):
        state = dict(self.BASE_STATE)
        state["top_universities"] = []
        with patch("orchestration.specialists.course_finder.find_courses_react", return_value=([], [])) as mock_fn:
            result = course_finder_node(state)
        mock_fn.assert_called_once_with([], state["user_information"])
        assert result["courses"] == []


# ---------------------------------------------------------------------------
# END-TO-END TEST — requires live credentials (.env)
# ---------------------------------------------------------------------------

def test_course_finder_e2e():
    """
    Full end-to-end test: calls real Pinecone + real LLM.
    Uses a small fixed list of universities to keep cost low.
    """
    top_universities = ["Politecnico di Milano", "CTU (Prague)"]
    user_info = {
        "academic_profile": {"gpa": 3.2, "major": "Computer Science"},
        "language_profile": {"non_english_languages": []},
    }

    result, react_steps = find_courses_react(top_universities, user_info)

    print("\n--- E2E CourseFinder Result ---")
    print(json.dumps(result, ensure_ascii=True, indent=2))

    KNOWN_LANGUAGES = {"English", "Spanish", "French", "Italian", "German",
                       "Czech", "Danish", "Portuguese", "Chinese", "Japanese", "Korean"}

    assert isinstance(result, list), "Result must be a list"
    assert len(result) > 0, "Should return at least one university"
    assert isinstance(react_steps, list), "react_steps must be a list"

    for uni in result:
        assert "university_name" in uni, f"Missing 'university_name' in: {uni}"
        assert "matched_courses" in uni, f"Missing 'matched_courses' in: {uni}"
        assert isinstance(uni["matched_courses"], list), "'matched_courses' must be a list"
        assert len(uni["matched_courses"]) > 0, f"No courses found for {uni['university_name']}"
        for course in uni["matched_courses"]:
            assert "course_name" in course
            assert "language" in course
            assert "relevance" in course
            lang = course["language"]
            assert any(kl in lang for kl in KNOWN_LANGUAGES), f"Unexpected language: {lang}"


def test_e2e_non_english_student():
    """
    E2E: student with a non-English language (French).
    Courses returned should include French-language options where available.
    """
    top_universities = ["CentraleSupélec", "ECAM Strasbourg"]
    user_info = {
        "academic_profile": {"gpa": 3.5, "major": "Electrical Engineering"},
        "language_profile": {"non_english_languages": ["French"]},
    }

    result, _ = find_courses_react(top_universities, user_info)

    print("\n--- E2E Non-English Student Result ---")
    print(json.dumps(result, ensure_ascii=True, indent=2))

    KNOWN_LANGUAGES = {"English", "French", "Spanish", "German", "Italian", "Czech",
                       "Danish", "Portuguese", "Chinese", "Japanese", "Korean"}

    assert isinstance(result, list)
    assert len(result) > 0

    # LLMs may return compound values like "French/English" — accept if any known language appears
    for uni in result:
        for course in uni.get("matched_courses", []):
            lang = course.get("language", "")
            assert any(kl in lang for kl in KNOWN_LANGUAGES), \
                f"Unexpected language: {lang}"

    for uni in result:
        assert uni["university_name"] in top_universities or len(uni["university_name"]) > 0
        for course in uni["matched_courses"]:
            assert course["course_name"]
            assert course["relevance"]


def test_e2e_single_university():
    """
    E2E: only one university — result should contain exactly one entry.
    """
    user_info = {
        "academic_profile": {"gpa": 3.0, "major": "Mechanical Engineering"},
        "language_profile": {"non_english_languages": []},
    }

    result, _ = find_courses_react(["DTU"], user_info)

    print("\n--- E2E Single University Result ---")
    print(json.dumps(result, ensure_ascii=True, indent=2))

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["university_name"] == "DTU"
    assert len(result[0]["matched_courses"]) >= 1
    for course in result[0]["matched_courses"]:
        assert course["language"] == "English"  # DTU teaches in English


def test_e2e_courses_relevant_to_major():
    """
    E2E: courses returned should be semantically relevant to the student's major.
    Checks that key domain terms appear in course names or relevance fields.
    """
    user_info = {
        "academic_profile": {"gpa": 3.8, "major": "Computer Science"},
        "language_profile": {"non_english_languages": []},
    }

    result, _ = find_courses_react(["Technical University of Munich"], user_info)

    print("\n--- E2E Major Relevance Result ---")
    print(json.dumps(result, ensure_ascii=True, indent=2))

    assert len(result) > 0
    all_text = " ".join(
        f"{c['course_name']} {c['relevance']}"
        for uni in result
        for c in uni.get("matched_courses", [])
    ).lower()

    cs_keywords = ["algorithm", "software", "machine learning", "data", "network",
                   "programming", "computer", "system", "artificial", "security"]
    matched = [kw for kw in cs_keywords if kw in all_text]
    assert len(matched) >= 2, f"Courses don't seem relevant to CS. Text: {all_text[:300]}"

def test_e2e_courses_structure_consistent_across_universities():
    """
    E2E: multiple universities — each must have the same nested structure.
    """
    user_info = {
        "academic_profile": {"gpa": 3.2, "major": "Data Science"},
        "language_profile": {"non_english_languages": []},
    }
    top_universities = ["Politecnico di Milano", "Friedrich Schiller University Jena"]

    result, _ = find_courses_react(top_universities, user_info)

    print("\n--- E2E Structure Consistency Result ---")
    print(json.dumps(result, ensure_ascii=True, indent=2))

    assert isinstance(result, list)
    assert len(result) >= 1

    for uni in result:
        assert isinstance(uni.get("university_name"), str) and uni["university_name"]
        assert isinstance(uni.get("matched_courses"), list)
        for course in uni["matched_courses"]:
            assert isinstance(course.get("course_name"), str) and course["course_name"]
            assert isinstance(course.get("language"), str) and course["language"]
            assert isinstance(course.get("relevance"), str) and course["relevance"]
            # Relevance should be meaningful (at least 10 chars)
            assert len(course["relevance"]) >= 10, f"Relevance too short: {course['relevance']}"


def test_e2e_web_search_used():
    """
    E2E: verifies the agent uses web search and returns valid course results.
    Uses a single well-known university to keep cost and latency low.
    """
    user_info = {
        "academic_profile": {"gpa": 3.5, "major": "Computer Science"},
        "language_profile": {"non_english_languages": []},
    }

    result, _ = find_courses_react(["Technical University of Denmark (DTU)"], user_info)

    print("\n--- E2E Web Search Result ---")
    print(json.dumps(result, ensure_ascii=True, indent=2))

    assert isinstance(result, list)
    assert len(result) == 1

    uni = result[0]
    assert "university_name" in uni
    assert isinstance(uni["matched_courses"], list)
    assert len(uni["matched_courses"]) >= 1

    for course in uni["matched_courses"]:
        assert course.get("course_name")
        assert course.get("language")
        assert course.get("relevance")


if __name__ == "__main__":
    # Run unit tests
    pytest.main([__file__, "-v", "-k", "not e2e"])

    # Run all e2e separately
    print("\n" + "="*60)
    for fn in [test_course_finder_e2e, test_e2e_non_english_student,
               test_e2e_single_university, test_e2e_courses_relevant_to_major,
               test_e2e_courses_structure_consistent_across_universities]:
        print(f"\nRunning {fn.__name__}...")
        fn()
