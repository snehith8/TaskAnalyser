from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .scoring import score_tasks
from .serializers import TaskSerializer
from .models import Task
from django.views.decorators.csrf import csrf_exempt

@api_view(['POST'])
def analyze_tasks(request):
    """
    POST /api/tasks/analyze/
    Body: JSON array of tasks. Each item should contain id,title,due_date,estimated_hours,importance,dependencies
    Returns: tasks sorted by calculated score with explanations.
    """
    data = request.data
    if not isinstance(data, list):
        return Response({"error": "Expected a JSON array of tasks"}, status=status.HTTP_400_BAD_REQUEST)

    # Basic validation & feed defaults
    tasks = []
    errors = []
    for i, t in enumerate(data):
        if not t.get('id'):
            # allow missing id: generate a temporary id prefixed with __tmp__
            import uuid
            t['id'] = f"__tmp__{uuid.uuid4()}"
        if not t.get('title'):
            errors.append({"index": i, "error": "missing title"})
            continue
        # sanitize importance
        try:
            t['importance'] = int(t.get('importance', 5))
        except Exception:
            t['importance'] = 5
        try:
            t['estimated_hours'] = float(t.get('estimated_hours', 1.0))
        except Exception:
            t['estimated_hours'] = 1.0
        deps = t.get('dependencies') or []
        if not isinstance(deps, list):
            deps = []
        t['dependencies'] = deps
        tasks.append(t)

    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    strategy = request.query_params.get('strategy', 'smart_balance')
    out = score_tasks(tasks, strategy=strategy)
    # build response: flattened list
    resp_list = []
    for r in out['results']:
        resp_list.append({
            'id': r['task']['id'],
            'title': r['task'].get('title'),
            'score': r['score'],
            'explanation': r['explanation'],
            'circular_dependency': r['circular_dependency'],
            'task': r['task']
        })
    return Response({
        'sorted_tasks': resp_list,
        'cycles': out['cycles']
    })

@api_view(['GET', 'POST'])
def suggest_tasks(request):
    """
    GET /api/tasks/suggest/
    Returns top 3 tasks from DB (or if POST with body list, uses that list).
    """
    if request.method == 'POST':
        tasks = request.data if isinstance(request.data, list) else []
    else:
        # load tasks from DB
        qs = Task.objects.all()
        serializer = TaskSerializer(qs, many=True)
        tasks = serializer.data

    if not tasks:
        return Response({'suggestions': [], 'message': 'no tasks found'}, status=status.HTTP_200_OK)

    strategy = request.query_params.get('strategy', 'smart_balance')
    out = score_tasks(tasks, strategy=strategy)
    top3 = out['results'][:3]
    suggestions = []
    for r in top3:
        t = r['task']
        suggestions.append({
            'id': t.get('id'),
            'title': t.get('title'),
            'score': r['score'],
            'why': r['explanation']
        })
    return Response({'suggestions': suggestions, 'cycles': out['cycles']})
