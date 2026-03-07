import pytest
from orchestration.specialists.ranker import rank_universities
from utils.config import supabase
import random

valid_universities_list = [
    {"name": "Technical University of Crete", "country": "Greece"},
    {"name": "Institut Supbiotech de Paris", "country": "France"},
    {"name": "ECE Engineering School", "country": "France"},
    {"name": "Alexandru Ioan Cuza University of Iasi", "country": "Romania"},
    {"name": "Politecnico di Torino", "country": "Italy"},
    {"name": "Politecnico di Milano", "country": "Italy"},
    {"name": "Instituto Tecnológico de Buenos Aires", "country": "Argentina"},
    {"name": "Universidad de Palermo", "country": "Argentina"},
    {"name": "MCI Management Center Innsbruck", "country": "Austria"},
    {"name": "Concordia University", "country": "Canada"},
    {"name": "McGill University", "country": "Canada"},
    {"name": "Polytechnique Montréal", "country": "Canada"},
    {"name": "Universidad Francisco de Vitoria", "country": "Spain"},
    {"name": "University of British Columbia", "country": "Canada"},
    {"name": "University of Manitoba", "country": "Canada"},
    {"name": "University of Toronto", "country": "Canada"},
    {"name": "KAIST", "country": "South Korea"},
    {"name": "ITESM Monterrey", "country": "Mexico"},
    {"name": "University of Erlangen-Nuremberg", "country": "Germany"},
    {"name": "Pontificia Universidad Catolica de Chile (PUC)", "country": "Chile"},
    {"name": "East China Normal University", "country": "China"},
    {"name": "Tongji University", "country": "China"},
    {"name": "Shanghai Jiao Tong University (SJTU)", "country": "China"},
    {"name": "Nanjing University", "country": "China"},
    {"name": "Nankai University", "country": "China"},
    {"name": "Guangdong Technion - Israel Institute of Technology", "country": "China"},
    {"name": "Peking University", "country": "China"},
    {"name": "Shandong University", "country": "China"},
    {"name": "University of Science and Technology of China", "country": "China"},
    {"name": "Tsinghua University", "country": "China"},
    {"name": "Friedrich Schiller University Jena", "country": "Germany"},
    {"name": "Technical University of Munich", "country": "Germany"},
    {"name": "Technical University of Berlin", "country": "Germany"},
    {"name": "University of Cyprus", "country": "Cyprus"},
    {"name": "Czech Technical University", "country": "Czech Republic"},
    {"name": "Inteli Institute of Technology and Leadership", "country": "Brazil"},
    {"name": "Technical University of Denmark (DTU)", "country": "Denmark"},
    {"name": "HEC School of Management", "country": "France"},
    {"name": "ENSCM National School of Chemistry Montpellier", "country": "France"},
    {"name": "Ecole Polytechnique Paris", "country": "France"},
    {"name": "Ecole Centrale Marseille", "country": "France"},
    {"name": "CentraleSupélec", "country": "France"},
    {"name": "PSL Dauphine", "country": "France"},
    {"name": "EPF – Engineering School", "country": "France"},
    {"name": "ECAM Strasbourg", "country": "France"},
    {"name": "VinUniversity", "country": "Vietnam"},
    {"name": "University of Connecticut", "country": "USA"},
    {"name": "University of Oregon", "country": "USA"},
    {"name": "Anhalt University of Applied Sciences", "country": "Germany"},
    {"name": "Karlsruhe Institute of Technology", "country": "Germany"},
    {"name": "Leibniz Universität Hannover", "country": "Germany"},
    {"name": "Technical University Darmstadt", "country": "Germany"},
    {"name": "University of Applied Sciences Bielefeld", "country": "Germany"},
    {"name": "RWTH Aachen University", "country": "Germany"},
    {"name": "Hong Kong University of Science and Technology", "country": "Hong Kong"},
    {"name": "City University of Hong Kong", "country": "Hong Kong"},
    {"name": "IIIT Pune", "country": "India"},
    {"name": "Sapienza University of Rome", "country": "Italy"},
    {"name": "Kyushu University", "country": "Japan"},
    {"name": "UDLAP", "country": "Mexico"},
    {"name": "Wroclaw University of Technology", "country": "Poland"},
    {"name": "Handong Global University", "country": "South Korea"},
    {"name": "POSTECH University", "country": "South Korea"},
    {"name": "Ajou University", "country": "South Korea"},
    {"name": "Sungkyunkwan University", "country": "South Korea"},
    {"name": "École Polytechnique Fédérale de Lausanne", "country": "Switzerland"},
    {"name": "Academia Sinica", "country": "Taiwan"},
    {"name": "National Cheng Kung University", "country": "Taiwan"},
    {"name": "National Taiwan University", "country": "Taiwan"},
    {"name": "National Tsing Hua University", "country": "Taiwan"},
    {"name": "National Yang Ming Chiao Tung University", "country": "Taiwan"},
    {"name": "Universidad ORT Uruguay", "country": "Uruguay"},
    {"name": "Carnegie Mellon University", "country": "USA"},
    {"name": "Cornell University", "country": "USA"}
]

def test_score_universities_with_llm():
    universities = random.sample(valid_universities_list, 12)  # Randomly select 20 universities for testing
    user_preferences = """
    I'm looking for a university with a really strong social scene where it's easy to make friends. 
    I'd love a proper campus vibe where students actually live and hang out together, not just a place where everyone commutes and leaves after class. 
    At the same time, I don't want to be isolated in the middle of nowhere—it needs to be close to a lively city full of art, good coffee shops, and nice parks to relax in. 
    Most importantly, I need to be in a safe, non-antisemitic place with a warm Jewish community around. I really want to have people to share Friday night dinners with so I don't feel alone.
    """
    top_k = 5
    result = rank_universities(universities, user_preferences, top_k=top_k)
    print("Top universities:", result)
    assert isinstance(result, list)
    assert len(result) <= top_k
    for uni_name in result:
        assert isinstance(uni_name, str)

if __name__ == "__main__":
    test_score_universities_with_llm()
