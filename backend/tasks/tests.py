from django.test import TestCase

# Create your tests here.
from .scoring import score_tasks

class ScoringTests(TestCase):
    def test_basic_scoring_and_sorting(self):
        tasks = [
            {'id': 't1', 'title': 'A', 'due_date': None, 'estimated_hours': 0.5, 'importance': 5, 'dependencies': []},
            {'id': 't2', 'title': 'B', 'due_date': '2025-12-01', 'estimated_hours': 8, 'importance': 9, 'dependencies': []},
            {'id': 't3', 'title': 'C', 'due_date': '2025-11-20', 'estimated_hours': 2, 'importance': 7, 'dependencies': ['t1']}
        ]
        out = score_tasks(tasks)
        results = out['results']
        # ensure results sorted descending
        scores = [r['score'] for r in results]
        self.assertTrue(scores[0] >= scores[1] >= scores[2])

    def test_cycle_detection(self):
        tasks = [
            {'id':'a', 'title':'A', 'due_date':None, 'estimated_hours':1, 'importance':5, 'dependencies':['b']},
            {'id':'b', 'title':'B', 'due_date':None, 'estimated_hours':1, 'importance':5, 'dependencies':['a']}
        ]
        out = score_tasks(tasks)
        cycles = out['cycles']
        self.assertTrue(len(cycles) >= 1)
