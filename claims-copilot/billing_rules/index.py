"""
FAISS index builder and searcher for billing rules.
Provides semantic search over CMS/OIG guidelines.
"""

import json
import os
import numpy as np
from typing import List, Dict, Optional
import hashlib

# Use simple TF-IDF + cosine similarity as fallback if FAISS unavailable
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("FAISS not available, using fallback search")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class BillingRulesIndex:
    """
    Semantic search index for billing rules.
    Uses FAISS if available, falls back to TF-IDF.
    """
    
    def __init__(self, rules_path: str = None):
        if rules_path is None:
            rules_path = os.path.join(
                os.path.dirname(__file__),
                'rules.json'
            )
        
        self.rules_path = rules_path
        self.rules = []
        self.patterns = []
        self.documents = []  # Combined text for each rule
        self.vectorizer = None
        self.tfidf_matrix = None
        self.faiss_index = None
        
        self._load_rules()
        self._build_index()
    
    def _load_rules(self):
        """Load rules from JSON file."""
        with open(self.rules_path, 'r') as f:
            data = json.load(f)
        
        self.rules = data.get('rules', [])
        self.patterns = data.get('patterns', [])
        
        # Create searchable documents
        self.documents = []
        
        for rule in self.rules:
            # Combine all text fields for searching
            text_parts = [
                rule.get('title', ''),
                rule.get('rule_text', ''),
                rule.get('summary', ''),
                rule.get('cpt_code', '') or '',
                ' '.join(rule.get('fraud_indicators', []))
            ]
            doc = ' '.join(text_parts)
            self.documents.append({
                'text': doc,
                'type': 'rule',
                'data': rule
            })
        
        for pattern in self.patterns:
            text_parts = [
                pattern.get('name', ''),
                pattern.get('description', ''),
                ' '.join(pattern.get('detection_criteria', []))
            ]
            doc = ' '.join(text_parts)
            self.documents.append({
                'text': doc,
                'type': 'pattern',
                'data': pattern
            })
        
        print(f"Loaded {len(self.rules)} rules and {len(self.patterns)} patterns")
    
    def _build_index(self):
        """Build search index."""
        if len(self.documents) == 0:
            return
        
        texts = [doc['text'] for doc in self.documents]
        
        # Build TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        if FAISS_AVAILABLE:
            # Convert to dense and build FAISS index
            dense_matrix = self.tfidf_matrix.toarray().astype('float32')
            
            # Normalize for cosine similarity
            norms = np.linalg.norm(dense_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1
            dense_matrix = dense_matrix / norms
            
            # Build FAISS index
            d = dense_matrix.shape[1]
            self.faiss_index = faiss.IndexFlatIP(d)  # Inner product (cosine after normalization)
            self.faiss_index.add(dense_matrix)
            
            print(f"Built FAISS index with {self.faiss_index.ntotal} documents")
        else:
            print("Built TF-IDF index (FAISS fallback)")
    
    def search(
        self,
        query: str,
        cpt_codes: List[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for relevant billing rules.
        
        Args:
            query: Search query (context about the case)
            cpt_codes: Optional list of CPT codes to prioritize
            top_k: Number of results to return
        
        Returns:
            List of matching rules with relevance scores
        """
        if len(self.documents) == 0:
            return []
        
        # Enhance query with CPT codes if provided
        if cpt_codes:
            query = f"{query} CPT {' '.join(cpt_codes)}"
        
        # Vectorize query
        query_vec = self.vectorizer.transform([query])
        
        if FAISS_AVAILABLE and self.faiss_index is not None:
            # Use FAISS
            query_dense = query_vec.toarray().astype('float32')
            norm = np.linalg.norm(query_dense)
            if norm > 0:
                query_dense = query_dense / norm
            
            scores, indices = self.faiss_index.search(query_dense, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    results.append({
                        'section_id': doc['data'].get('section_id') or doc['data'].get('pattern_id'),
                        'type': doc['type'],
                        'title': doc['data'].get('title') or doc['data'].get('name'),
                        'rule_text': doc['data'].get('rule_text') or doc['data'].get('description'),
                        'summary': doc['data'].get('summary', ''),
                        'relevance_score': float(score),
                        'fraud_indicators': doc['data'].get('fraud_indicators') or doc['data'].get('detection_criteria', []),
                        'cpt_code': doc['data'].get('cpt_code')
                    })
        else:
            # Fallback to sklearn cosine similarity
            similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
            top_indices = similarities.argsort()[-top_k:][::-1]
            
            results = []
            for idx in top_indices:
                score = similarities[idx]
                if score > 0:
                    doc = self.documents[idx]
                    results.append({
                        'section_id': doc['data'].get('section_id') or doc['data'].get('pattern_id'),
                        'type': doc['type'],
                        'title': doc['data'].get('title') or doc['data'].get('name'),
                        'rule_text': doc['data'].get('rule_text') or doc['data'].get('description'),
                        'summary': doc['data'].get('summary', ''),
                        'relevance_score': float(score),
                        'fraud_indicators': doc['data'].get('fraud_indicators') or doc['data'].get('detection_criteria', []),
                        'cpt_code': doc['data'].get('cpt_code')
                    })
        
        # Boost results matching CPT codes
        if cpt_codes:
            for result in results:
                if result.get('cpt_code') in cpt_codes:
                    result['relevance_score'] *= 1.5
            results.sort(key=lambda x: -x['relevance_score'])
        
        return results
    
    def get_rule_by_id(self, section_id: str) -> Optional[Dict]:
        """Get a specific rule by section ID."""
        for rule in self.rules:
            if rule.get('section_id') == section_id:
                return rule
        
        for pattern in self.patterns:
            if pattern.get('pattern_id') == section_id:
                return pattern
        
        return None
    
    def get_rules_for_cpt(self, cpt_code: str) -> List[Dict]:
        """Get all rules related to a specific CPT code."""
        results = []
        
        for rule in self.rules:
            if rule.get('cpt_code') == cpt_code:
                results.append(rule)
        
        return results
    
    def get_pattern_by_name(self, pattern_name: str) -> Optional[Dict]:
        """Get a fraud pattern by name or ID."""
        pattern_name_lower = pattern_name.lower()
        
        for pattern in self.patterns:
            if (pattern.get('pattern_id', '').lower() == pattern_name_lower or
                pattern.get('name', '').lower() == pattern_name_lower or
                pattern_name_lower in pattern.get('name', '').lower()):
                return pattern
        
        return None


# Singleton instance
_index_instance = None


def get_billing_rules_index() -> BillingRulesIndex:
    """Get or create the billing rules index singleton."""
    global _index_instance
    if _index_instance is None:
        _index_instance = BillingRulesIndex()
    return _index_instance


def search_billing_rules(
    cpt_codes: List[str] = None,
    context: str = "",
    top_k: int = 5
) -> List[Dict]:
    """
    Search billing rules (convenience function).
    
    Args:
        cpt_codes: List of CPT codes to search for
        context: Additional context about the case
        top_k: Number of results
    
    Returns:
        List of relevant rules
    """
    index = get_billing_rules_index()
    return index.search(context, cpt_codes=cpt_codes, top_k=top_k)


if __name__ == "__main__":
    # Test the index
    index = BillingRulesIndex()
    
    print("\n=== Test Search: Upcoding ===")
    results = index.search("provider upcoding high volume billing", top_k=3)
    for r in results:
        print(f"\n{r['section_id']} (score: {r['relevance_score']:.2f})")
        print(f"  {r['title']}")
        print(f"  {r['summary']}")
    
    print("\n=== Test Search: CPT 27447 ===")
    results = index.search("knee replacement suspicious volume", cpt_codes=['27447'], top_k=3)
    for r in results:
        print(f"\n{r['section_id']} (score: {r['relevance_score']:.2f})")
        print(f"  {r['title']}")
    
    print("\n=== Test Search: Referral kickback ===")
    results = index.search("referral concentration shift sudden change", top_k=3)
    for r in results:
        print(f"\n{r['section_id']} (score: {r['relevance_score']:.2f})")
        print(f"  {r['title']}")
    
    print("\n=== Get Pattern: Upcoding Ring ===")
    pattern = index.get_pattern_by_name("upcoding ring")
    if pattern:
        print(f"Pattern: {pattern['name']}")
        print(f"Criteria: {pattern['detection_criteria']}")
