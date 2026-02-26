import os
import json

def analyze_universities(top_universities, extracted_data_dict, rag_query_func):
    """
    Provides deeper analysis for each university using previously extracted data and RAG querying Pinecone for defined categories.

    Args:
        top_universities (list): List of dicts with 'university_name' and 'country'.
        extracted_data_dict (dict): Dict mapping university names to extracted data from previous stages.
        rag_query_func (callable): Function that takes (university_name, country) and returns category dict from Pinecone.

    Returns:
        list[dict]: List of analysis dicts for each university.
    """
    analysis_results = []
    for uni in top_universities:
        uni_name = uni.get("university_name") or uni.get("name")
        country = uni.get("country")
        categories = rag_query_func(uni_name, country)
        uni_analysis = {
            "university_name": uni_name,
            "country": country,
            "extracted_data": extracted_data_dict.get(uni_name, {}),
            "category_analysis": categories
        }
        analysis_results.append(uni_analysis)
    return analysis_results
