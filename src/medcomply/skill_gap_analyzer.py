from typing import Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .settings import Settings

_WEAK_THRESHOLD = 0.6
_MIN_COHORT_FOR_CLUSTERING = 3


class SkillGapAnalyzer:
    """
    Semantic similarity scoring (cosine distance over bge-base-en-v1.5 embeddings)
    with KMeans cohort theme detection.
    """

    def __init__(self, settings: Settings):
        self._model = SentenceTransformer(settings.dense_model)

    def score_answer(self, employee_answer: str, canonical_answer: str) -> float:
        """Cosine similarity between embedded employee and canonical answers. Returns 0–1."""
        vecs = self._model.encode(
            [employee_answer, canonical_answer], show_progress_bar=False
        )
        return float(cosine_similarity([vecs[0]], [vecs[1]])[0][0])

    def analyze_employee(self, employee_id: str, responses: List[Dict]) -> Dict:
        """
        Score an employee's free-text answers against canonical answers.

        Each response dict must have keys: question, canonical_answer, employee_answer, category.
        Returns employee_id, overall_score, category_scores, weak_categories.
        """
        if not responses:
            return {
                "employee_id": employee_id,
                "overall_score": 0.0,
                "category_scores": {},
                "weak_categories": [],
            }

        texts = []
        for r in responses:
            texts.append(r["employee_answer"])
            texts.append(r["canonical_answer"])

        vecs = self._model.encode(texts, show_progress_bar=False)

        scores_by_category: Dict[str, List[float]] = {}
        for i, r in enumerate(responses):
            emp_vec = vecs[i * 2]
            can_vec = vecs[i * 2 + 1]
            sim = float(cosine_similarity([emp_vec], [can_vec])[0][0])
            cat = r["category"]
            scores_by_category.setdefault(cat, []).append(sim)

        category_scores = {
            cat: float(np.mean(sims)) for cat, sims in scores_by_category.items()
        }
        overall_score = float(np.mean(list(category_scores.values())))
        weak_categories = [
            cat for cat, score in category_scores.items() if score < _WEAK_THRESHOLD
        ]

        return {
            "employee_id": employee_id,
            "overall_score": overall_score,
            "category_scores": category_scores,
            "weak_categories": weak_categories,
        }

    def cohort_themes(self, analyses: List[Dict]) -> List[str]:
        """
        Cluster per-employee weakness vectors and return a list of theme labels.

        Takes the mean embedding of each employee's weak-category answer texts,
        runs KMeans (n_clusters=3), and labels each centroid with its closest
        weak-category name. Returns [] when fewer than _MIN_COHORT_FOR_CLUSTERING
        employees have identified weaknesses.
        """
        from sklearn.cluster import KMeans

        weak_records = [a for a in analyses if a.get("weak_categories")]
        if len(weak_records) < _MIN_COHORT_FOR_CLUSTERING:
            return []

        # Build one embedding per employee: mean over their weak-category names
        employee_vecs = []
        for record in weak_records:
            cat_texts = record["weak_categories"]
            vecs = self._model.encode(cat_texts, show_progress_bar=False)
            employee_vecs.append(vecs.mean(axis=0))

        X = np.array(employee_vecs)
        n_clusters = min(3, len(X))
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        km.fit(X)

        # Label each centroid with the closest weak-category name across all employees
        all_cats = list({cat for r in weak_records for cat in r["weak_categories"]})
        cat_vecs = self._model.encode(all_cats, show_progress_bar=False)
        themes = []
        for centroid in km.cluster_centers_:
            sims = cosine_similarity([centroid], cat_vecs)[0]
            themes.append(all_cats[int(np.argmax(sims))])

        return themes
