from datetime import date
from math import exp

MAX_URGENCY_WINDOW_DAYS = 30  # window to normalize urgency
PAST_DUE_BOOST_PER_DAY = 0.02  # extra urgency per day past due

def _sigmoid(x):
    # simple sigmoid scaled to 0..1, where larger x -> smaller quick-win score
    # we want small estimated_hours -> score close to 1
    # map hours to a number and use logistic
    return 1 / (1 + exp(0.25 * (x - 4)))  # tweak constants for desirable curve

def normalized_importance(importance):
    if importance is None:
        return 0.5
    return max(0.0, min(1.0, importance / 10.0))

def urgency_score(due_date):
    """
    Returns a value roughly between 0 and >1 (past-due gives bonus).
    Closer dates -> higher score.
    """
    if due_date is None:
        return 0.2  # low urgency if no date
    today = date.today()
    delta = (due_date - today).days
    if delta >= 0:
        # future: normalize to 0..1 (0 far future, 1 due today)
        frac = max(0.0, min(1.0, 1 - (delta / MAX_URGENCY_WINDOW_DAYS)))
        return frac
    else:
        # past due -> add boost
        past_days = abs(delta)
        return 1.0 + min(0.5, past_days * PAST_DUE_BOOST_PER_DAY)

def effort_score(estimated_hours):
    if estimated_hours is None or estimated_hours <= 0:
        return 1.0
    return float(_sigmoid(estimated_hours))

def dependency_score(task_id, all_tasks_map):
    """
    If a task is a blocker (other tasks depend on it), return 1, else 0.
    We'll compute number of dependents and normalize (capped).
    """
    dependents = 0
    for t in all_tasks_map.values():
        deps = t.get('dependencies') or []
        if task_id in deps:
            dependents += 1
    # normalize: 0 -> 0, 1 -> 0.6, 2+ -> 1.0
    if dependents == 0:
        return 0.0
    if dependents == 1:
        return 0.6
    return 1.0

def detect_cycles(all_tasks_map):
    # build adjacency: node -> list of dependencies (edges node->dep)
    graph = {tid: list(all_tasks_map[tid].get('dependencies') or []) for tid in all_tasks_map}
    visited = {}
    cycles = []

    def dfs(node, stack):
        if node not in graph:
            return False
        if visited.get(node) == 1:
            # in current recursion stack -> cycle
            cycles.append(list(stack + [node]))
            return True
        if visited.get(node) == 2:
            return False
        visited[node] = 1
        for neigh in graph[node]:
            dfs(neigh, stack + [node])
        visited[node] = 2
        return False

    for n in graph:
        if visited.get(n) is None:
            dfs(n, [])
    return cycles

DEFAULT_WEIGHTS = {
    'urgency': 0.35,
    'importance': 0.35,
    'effort': 0.20,
    'dependency': 0.10
}

STRATEGY_PRESETS = {
    'fastest_wins': {'urgency': 0.2, 'importance': 0.2, 'effort': 0.5, 'dependency': 0.1},
    'high_impact': {'urgency': 0.2, 'importance': 0.6, 'effort': 0.1, 'dependency': 0.1},
    'deadline_driven': {'urgency': 0.7, 'importance': 0.15, 'effort': 0.1, 'dependency': 0.05},
    'smart_balance': DEFAULT_WEIGHTS
}

def score_tasks(task_list, strategy='smart_balance'):
    # Create map for fast lookups
    tasks_map = {t.get('id'): t for t in task_list}
    cycles = detect_cycles(tasks_map)

    weights = STRATEGY_PRESETS.get(strategy, DEFAULT_WEIGHTS)

    results = []
    for t in task_list:
        tid = t.get('id')
        # parse fields safely
        importance = t.get('importance', 5)
        est_hours = t.get('estimated_hours', 1.0)
        due_date = t.get('due_date')  # expected as date object or ISO string
        # if string, try to parse to date
        from datetime import datetime
        if isinstance(due_date, str):
            try:
                due_date = datetime.fromisoformat(due_date).date()
            except Exception:
                due_date = None
        u = urgency_score(due_date)
        imp = normalized_importance(importance)
        eff = effort_score(est_hours)
        dep = dependency_score(tid, tasks_map)

        composite = (weights['urgency'] * u +
                     weights['importance'] * imp +
                     weights['effort'] * eff +
                     weights['dependency'] * dep)

        # scale to 0..100
        score = round(composite * 100, 2)

        explanation_parts = []
        explanation_parts.append(f"urgency({round(u,2)})*{weights['urgency']}")
        explanation_parts.append(f"importance({round(imp,2)})*{weights['importance']}")
        explanation_parts.append(f"effort({round(eff,2)})*{weights['effort']}")
        if dep > 0:
            explanation_parts.append(f"dependency({round(dep,2)})*{weights['dependency']}")

        explanation = "; ".join(explanation_parts)

        # annotate if task part of a cycle
        in_cycle = any(tid in cycle for cycle in cycles)
        if in_cycle:
            explanation += " | Note: involved in circular dependency"

        results.append({
            'task': t,
            'score': score,
            'explanation': explanation,
            'circular_dependency': in_cycle
        })

    # sort descending by score
    results.sort(key=lambda x: x['score'], reverse=True)
    return {
        'results': results,
        'cycles': cycles
    }
