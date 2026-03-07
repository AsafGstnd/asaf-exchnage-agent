from utils.llmod_client import llmod_chat
import json
import os
from data_pipeline.context_data import FINANCIAL_REFERENCE_TABLE, SOCIAL_SENTIMENT_TABLE

def rank_universities(valid_universities_list, user_preferences, top_k=5):
    """
    Ranks universities by calling score_universities_with_llm and process_llm_scores.
    Args:
        valid_universities_list (list): List of dicts with 'name' and 'country'.
        user_preferences (str): Student preferences as a string.
        top_k (int): Number of top universities to return.
    Returns:
        list[dict]: Ranked top k universities with scores and reasoning.
    """
    llm_json_response = score_universities_with_llm(valid_universities_list, user_preferences, top_k)
    # The Pytest Hack: Only prints if a test is currently running
    if os.getenv("PYTEST_CURRENT_TEST"):
        print("\n--- DEBUG: LLM JSON RESPONSE ---")
        print(json.dumps(llm_json_response, ensure_ascii=False, indent=2))
        print("-------------------------------")
    return process_llm_scores(llm_json_response, top_k=top_k)

def score_universities_with_llm(valid_universities_list, user_preferences, top_k=5, return_prompt=False):
    """
    Sends ranking prompt to LLM, parses response, and returns ranked universities.
    Args:
        valid_universities_list (list): List of dicts with 'name' and 'country'.
        user_preferences (str): Student preferences as a string.
        top_k (int): Number of top universities to return.
        return_prompt (bool): If True, return (llm_json_response, prompt_dict).
    Returns:
        llm_json_response (or tuple if return_prompt)
    """
    system_prompt = """You are an elite study-abroad placement API. Rank a list of eligible universities based on a student's preferences. Rely on your internal knowledge of global universities, cultures, and geography. Return ONLY valid JSON. No markdown, no explanations."""

    # Format eligible universities as a list of dicts with name and country
    formatted_universities = [
        {"university_name": uni["name"], "country": uni["country"]}
        for uni in valid_universities_list if uni.get("name") and uni.get("country")
    ]

    user_prompt = f"""
    Eligible Universities:
    {json.dumps(formatted_universities, ensure_ascii=False, indent=2)}

    Social Media Sentiment Table:
    {SOCIAL_SENTIMENT_TABLE}
    
    Reference Data for `financial_fit` (Global Semester Pure Cost - $0 Tuition):
    {FINANCIAL_REFERENCE_TABLE}

    Student Preferences: "{user_preferences}"

    Rules:
    1. Evaluate and score EVERY university in the provided list based on how well it matches the user's input. 
    2. Grade each university (0-100) across these categories ONLY if the user's input relates to them. If a category is irrelevant to the prompt, output `null`
    - `academic_fit`: Score based strictly on the university's standing in the Shanghai Ranking (ARWU). 
        Reward high research output, STEM focus, and global prestige. Penalize universities that lack a global research footprint.
    - `lifestyle_fit`: Score the combined physical routine and social atmosphere. Evaluate the physical routine based on Campus Typology (enclosed residential bubble vs. 
        decentralized commuter school), City Scale (immersive college town vs. sprawling megacity), and Academic Pacing (hyper-competitive "pressure-cooker" vs. balanced workload). 
        Evaluate the social atmosphere based on the party vibe, ease of making friends, and international/Erasmus presence. Use your internal knowledge alongside the provided social media sentiment table as general assistance.
    - `location_fit`: Nature/hikes, nightlife, art, culture, weather.
    - `financial_fit`: Total cost of exchange (rent, food, travel). Base the score on the "Reference Data" table provided. 
        Use your internal knowledge to adjust the score/estimate slightly if the specific city or country is an outlier 
        (e.g., Zurich is more expensive than the "Western Europe" average). In the reasoning, provide a brief estimated total cost (e.g., ~$12k) for the semester.
    - `jewish_israeli_community_fit`: Evaluate EXCLUSIVELY based on current antisemitism levels on and around campus, the accessibility of the local Jewish community (e.g., Chabad, synagogues, kosher food), and the presence of Israeli students or locals. 
        STRICTLY IGNORE general city crime rates, pickpocketing, or broad safety metrics.
    - `other_preferences_fit`: Any specific user requests that do not fit into the above categories (e.g., specific sports, dietary needs, unique hobbies).
    3. Provide a short `reasoning` explicitly referencing the evaluated traits.

    Return ONLY a JSON object with this exact structure:
    {{
        "scored_universities": [
            {{
                "university_name": "string",
                "country": "string",
                "scores": {{
                    "academic_fit": int or null,
                    "lifestyle_fit": int or null,
                    "social_fit": int or null,
                    "location_fit": int or null,
                    "financial_fit": int or null,
                    "jewish_israeli_community_fit": int or null,
                    "other_preferences_fit": int or null
                }},
                "reasoning": "string"
            }}
        ]
    }}
    """

    response_text = llmod_chat(system_prompt, user_prompt, use_json=True)
    llm_json_response = json.loads(response_text)
    if return_prompt:
        return llm_json_response, {"system_prompt": system_prompt[:200] + "...", "user_prompt": user_prompt, "top_k": top_k}
    return llm_json_response

def process_llm_scores(llm_json_response, top_k=5):
    """
    Processes LLM scoring response, calculates a weighted average score, 
    ranks, and outputs top k universities.

    Args:
        llm_json_response (dict): LLM response with 'scored_universities' list.
        top_k (int): Number of top universities to return.

    Returns:
        list[dict]: Ranked top k universities with scores and reasoning.
    """
    
    # Define your weighting strategy (Currently set to equal weights)
    # NOTE FOR FUTURE: You can easily adjust these floats later to prioritize 
    CATEGORY_WEIGHTS = {
        "academic_fit": 1.0,
        "lifestyle_fit": 1.0,
        "social_fit": 1.0,
        "location_fit": 1.0,
        "financial_fit": 1.0,
        "jewish_israeli_community_fit": 1.0,
        "other_preferences_fit": 1.0
    }

    universities = llm_json_response.get("scored_universities", [])
    
    for uni in universities:
        scores = uni.get("scores", {})
        
        weighted_sum = 0
        total_weight_used = 0
        
        # Calculate the normalized weighted average
        for category, score in scores.items():
            if score is not None:
                weight = CATEGORY_WEIGHTS.get(category, 1.0)
                weighted_sum += (score * weight)
                total_weight_used += weight
                
        # Assign the final math, guarding against division by zero
        if total_weight_used > 0:
            uni["total_score"] = round(weighted_sum / total_weight_used)
        else:
            uni["total_score"] = 0
            
    universities.sort(key=lambda x: x.get("total_score", 0), reverse=True)
    
    for index, uni in enumerate(universities):
        uni["rank"] = index + 1

    return [uni["university_name"] for uni in universities[:top_k]]