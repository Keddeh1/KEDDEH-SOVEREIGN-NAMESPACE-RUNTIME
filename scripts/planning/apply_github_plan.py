#!/usr/bin/env python3
"""Apply the admitted programme to GitHub issues without inventing Project access."""
import json
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
REPO = 'Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME'
def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)
labels = {
    'status:queued': ('C5DEF5', 'Planned work awaiting dependency and acceptance gates'),
    'status:in-progress': ('1D76DB', 'Engineering or qualification actively underway'),
    'status:blocked': ('B60205', 'Explicit external prerequisite prevents completion'),
    'status:verified': ('006B75', 'Executed acceptance evidence recorded'),
    'priority:critical': ('B60205', 'Runtime continuity or integrity failure'),
    'priority:high': ('D93F0B', 'Next required delivery or qualification work'),
}
for name, (color, description) in labels.items():
    gh('label', 'create', name, '--repo', REPO, '--color', color,
       '--description', description, '--force')
tracking = json.loads((ROOT/'docs/research/GITHUB_TRACKING.json').read_text())
for batch in tracking['batches']:
    number = batch['number']
    status = 'status:verified' if batch['status']=='completed' else ('status:in-progress' if batch['batch']==3 else 'status:queued')
    gh('issue', 'edit', str(number), '--repo', REPO, '--add-label', status,
       '--add-assignee', 'Keddeh1')
for number in (19,20):
    gh('issue','edit',str(number),'--repo',REPO,'--add-label','priority:critical')
gh('issue','edit','27','--repo',REPO,'--add-label','status:in-progress','--add-assignee','Keddeh1')
print(json.dumps({'repository':REPO,'batch_issues_updated':10,'programme_issue_updated':27,'labels_applied':list(labels)}))
