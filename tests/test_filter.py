from orchestration.specialists.filter import filter_universities
from user_profiles import get_student_profiles
"""
Test file for simulating student input and testing filtering logic.
"""

def test_filter_universities(profile_name):
    profiles = get_student_profiles()
    if profile_name not in profiles:
        print(f"Profile '{profile_name}' not found. Available profiles: {list(profiles.keys())}")
        return
    student_input = profiles[profile_name]
    print(f"\n--- Testing profile: {profile_name} ---")
    result = filter_universities(student_input)
    print("\nFilter result:")
    print(result)
    assert isinstance(result, dict)
    assert "universities" in result
    assert isinstance(result["universities"], list)
    print(f"\nNumber of universities returned: {len(result['universities'])}")
    print("Universities returned:")
    for uni in result["universities"]:
        print(uni)

if __name__ == "__main__":
    profiles = get_student_profiles()
    print("Available profiles:", list(profiles.keys()))
    # Set the profile name to test here
    profile = "english_only_freshman"  
    test_filter_universities(profile)
