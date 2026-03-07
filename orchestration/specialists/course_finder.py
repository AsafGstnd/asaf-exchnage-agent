"""
ReAct agent for finding courses at universities that match the student's
major and language profile.

Uses a manual ReAct loop (Reason -> Act -> Observe) with llmod_chat()
and tools from the central registry (cached RAG + web search).
"""
import json
import re
from utils.llmod_client import llmod_chat
from tools.registry import TOOLS

TOOLS_DESCRIPTION = """Available tools (use exact format):
- search_web(query): Search the web for real-time course catalog or exchange program info.
  Format: Action: search_web | Args: {"query": "..."}
- search_factsheets(university, query): Search a university's factsheet for course, department, or language-of-instruction info.
  Format: Action: search_factsheets | Args: {"university": "...", "query": "..."}"""


# ---------------------------------------------------------------------------
# REACT LOOP
# ---------------------------------------------------------------------------

def _react_loop(system_prompt: str, user_prompt: str, max_iter: int = 4) -> str:
    """
    Manual ReAct loop using llmod_chat.
    Iterates until the LLM outputs 'Final Answer:' or max_iter is reached.
    """
    history_parts = [user_prompt]

    for _ in range(max_iter):
        context = "\n\n".join(history_parts)
        response = llmod_chat(system_prompt, context, use_json=False)
        print(f"[CourseFinder] LLM response: {response[:200]}...")

        if "Final Answer:" in response:
            return response.split("Final Answer:", 1)[1].strip()

        # Parse: Action: tool_name | Args: {...}
        action_match = re.search(
            r"Action:\s*(\w+)\s*\|\s*Args:\s*(\{.*?\})",
            response,
            re.DOTALL
        )
        if action_match:
            tool_name = action_match.group(1).strip()
            try:
                args = json.loads(action_match.group(2))
            except json.JSONDecodeError:
                args = {}
            tool_fn = TOOLS.get(tool_name)
            observation = tool_fn(**args) if tool_fn else f"Unknown tool: {tool_name}"
            print(f"[CourseFinder] Tool '{tool_name}' called, observation length: {len(observation)}")
            history_parts.append(f"Thought: {response}\nObservation: {observation}")
        else:
            # No tool call and no Final Answer — treat response as the final output
            return response

    # Fallback: force finalization
    context = "\n\n".join(history_parts) + "\n\nNow provide your Final Answer."
    return llmod_chat(system_prompt, context, use_json=False)


# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------

def find_courses_react(top_universities: list, user_information: dict) -> list:
    """
    ReAct agent that finds courses per university matching the student's
    major and language profile.

    Args:
        top_universities: List of university name strings from the ranker.
        user_information: The full student profile dict from AgentState.

    Returns:
        List[dict] — one dict per university with 'university_name' and 'matched_courses'.
    """
    major = user_information.get("academic_profile", {}).get("major", "")
    non_english = user_information.get("language_profile", {}).get("non_english_languages", [])
    languages = ["English"] + (non_english or [])

    system_prompt = f"""You are a course matching specialist for university exchange programs.
You have tools to find real course information.

{TOOLS_DESCRIPTION}

Reasoning format (strictly follow this):
Thought: <your reasoning about what to do next>
Action: <tool_name> | Args: <json args>
Observation: <tool result — provided by the system>
... (repeat Thought/Action/Observation as needed)
Final Answer: <valid JSON only, no markdown code blocks>

When finished, output exactly:
Final Answer: {{"universities": [{{"university_name": "...", "matched_courses": [{{"course_name": "...", "language": "...", "relevance": "..."}}]}}]}}"""

    user_prompt = f"""Find matching courses for a student at the following universities: {top_universities}

Student major: {major}
Student languages (courses MUST be taught in one of these): {languages}

For each university:
1. Call search_web with a query like "[university name] {major} courses exchange students" to find real course listings.
2. Optionally call search_factsheets to supplement with internal factsheet data.
3. Based on what you find, suggest 3-5 specific courses that:
   - Are taught in one of: {languages}
   - Are relevant to the student's major: {major}
   - Are typically open to exchange students

Final Answer must be valid JSON:
{{"universities": [{{"university_name": "...", "matched_courses": [{{"course_name": "...", "language": "...", "relevance": "1 sentence"}}]}}]}}"""

    raw = _react_loop(system_prompt, user_prompt)

    # Parse JSON from the final answer
    try:
        data = json.loads(raw)
        return data.get("universities", [])
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group()).get("universities", [])
            except Exception:
                pass
    return []
