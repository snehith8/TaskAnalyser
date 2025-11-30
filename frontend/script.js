const localTasks = [];

function el(id){ return document.getElementById(id); }

el('task-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const t = {
    id: 'local_'+Date.now(),
    title: el('title').value,
    due_date: el('due_date').value || null,
    estimated_hours: parseFloat(el('estimated_hours').value) || 1,
    importance: parseInt(el('importance').value) || 5,
    dependencies: el('dependencies').value ? el('dependencies').value.split(',').map(s=>s.trim()) : []
  };
  localTasks.push(t);
  alert('Task added to local list. Click Analyze to process.');
  el('task-form').reset();
});

el('analyze-btn').addEventListener('click', async () => {
  let tasks = [];
  const bulk = el('bulk').value.trim();
  if(bulk){
    try {
      tasks = JSON.parse(bulk);
      if(!Array.isArray(tasks)){ alert('Bulk JSON must be an array'); return; }
    } catch(err){
      alert('Invalid JSON: '+err.message); return;
    }
  }
  // combine local tasks
  tasks = tasks.concat(localTasks);

  if(tasks.length === 0){
    alert('No tasks to analyze');
    return;
  }

  const strategy = el('strategy').value;
  try {
    const res = await fetch('http://127.0.0.1:8000/api/tasks/analyze/?strategy=' + encodeURIComponent(strategy), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(tasks)
    });
    const data = await res.json();
    if(!res.ok){ alert(JSON.stringify(data)); return; }
    renderResults(data.sorted_tasks);
  } catch(err){
    alert('Network error: '+err.message);
  }
});

function renderResults(list){
  const container = el('results');
  container.innerHTML = '';
  list.forEach(item => {
    const d = document.createElement('div');
    d.className = 'task ' + priorityClass(item.score);
    d.innerHTML = `<strong>${item.title}</strong> <small>score: ${item.score}</small>
      <div>${item.explanation}</div>
      <pre>${JSON.stringify(item.task, null, 2)}</pre>`;
    container.appendChild(d);
  });
}

function priorityClass(score){
  if(score >= 70) return 'priority-high';
  if(score >= 40) return 'priority-medium';
  return 'priority-low';
}
