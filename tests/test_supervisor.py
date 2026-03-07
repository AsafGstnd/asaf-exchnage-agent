"""
Test for Supervisor agent orchestration logic.
"""
from orchestration.supervisor import Supervisor
from tests.test_filter import get_student_profiles

def test_supervisor_run():
    supervisor = Supervisor()
    profiles = get_student_profiles()
    profile_name = "default"  # Change to "high_gpa" or "low_gpa" to test other profiles
    profile = profiles[profile_name]
    print(f"\n=== Supervisor Test: Profile '{profile_name}' ===")
    print("\nRunning Supervisor agent...")
    result = supervisor.run(user_profile_dict=profile)
    assert "analysis" in result
    assert "steps" in result
    print("\n--- Final Analysis ---")
    print(result["analysis"])
    print("\n--- Execution Steps ---")
    for i, step in enumerate(result["steps"], 1):
        print(f"Step {i}: {step['module']}")
        print("  Prompt:")
        print(f"    {step['prompt']}")
        print("  Response:")
        print(f"    {step['response']}")
    # Save AgentState after first run
    import json
    agent_state_path = "agent_state_snapshot.json"
    config = {"configurable": {"thread_id": "user_123"}}
    agent_state = supervisor.app.get_state(config).values
    with open(agent_state_path, "w", encoding="utf-8") as f:
        json.dump(agent_state, f, ensure_ascii=False, indent=2)
    print(f"\nAgentState saved to {agent_state_path}")

def demo_analysis(use_offline=False):
    import json
    from orchestration.supervisor import _format_analysis_as_string
    agent_state_path = "agent_state_snapshot.json"
    if use_offline:
        print(f"\n[Demo] Loading AgentState from {agent_state_path}...")
        with open(agent_state_path, "r", encoding="utf-8") as f:
            agent_state = json.load(f)
    else:
        supervisor = Supervisor()
        profiles = get_student_profiles()
        profile_name = "default"
        profile = profiles[profile_name]
        result = supervisor.run(user_profile_dict=profile)
        config = {"configurable": {"thread_id": "user_123"}}
        agent_state = supervisor.app.get_state(config).values
    # Use the analysis formatting function
    analysis_results = agent_state.get("analysis", "")
    print("\n--- Demo Analysis ---")
    print(analysis_results)

if __name__ == "__main__":
    test_supervisor_run()
    # To demo analysis from offline state, call:
    # demo_analysis(use_offline=True)
