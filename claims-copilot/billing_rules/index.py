"""
Insurance regulatory rules index with TF-IDF search.
"""

import json
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class InsuranceRulesIndex:
    def __init__(self):
        rules_path = os.path.join(os.path.dirname(__file__), "rules.json")
        with open(rules_path, "r") as f:
            data = json.load(f)
        self.rules = data["rules"]
        self.patterns = data.get("patterns", {})

        # Build TF-IDF index
        self.documents = []
        for rule in self.rules:
            text = f"{rule['title']} {rule['rule_text']} {rule['summary']} {' '.join(rule.get('fraud_indicators', []))}"
            self.documents.append(text)

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)

    def search(self, query: str, top_k: int = 5):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_idx = np.argsort(scores)[-top_k:][::-1]

        results = []
        for idx in top_idx:
            if scores[idx] > 0.01:
                rule = self.rules[idx].copy()
                rule["relevance_score"] = round(float(scores[idx]), 4)
                results.append(rule)
        return results


_index = None

def get_insurance_rules_index():
    global _index
    if _index is None:
        _index = InsuranceRulesIndex()
    return _index

def search_insurance_rules(context: str, case_type: str = "", top_k: int = 5):
    """Search insurance rules by context and case type."""
    idx = get_insurance_rules_index()
    query = f"{case_type} {context}"
    return idx.search(query, top_k)
