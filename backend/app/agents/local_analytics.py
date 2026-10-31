"""A transparent keyword router over existing read-only queries; not a DL model."""
import json
from app.agents.analytics_agent import _run_tool
from app.agents import trace


def run_local_analytics(question, db):
    text = question.lower()
    start = trace.start()
    if any(x in text for x in ['equipment','damag','lost','gear']):
        tool = 'equipment_issues'
    elif 'fine' in text:
        tool = 'fines_by_student' if any(x in text for x in ['student','who']) else 'summary'
    elif any(x in text for x in ['peak','busiest hour','busy hour','booking hour']):
        tool = 'peak_hours'
    elif 'sport' in text:
        tool = 'by_sport'
    elif 'department' in text:
        tool = 'by_department'
    elif 'year' in text:
        tool = 'by_year'
    elif any(x in text for x in ['trend','daily','per day']):
        tool = 'trend'
    elif any(x in text for x in ['top student','most active','frequent']):
        tool = 'top_students'
    elif any(x in text for x in ['summary','total','no-show','no show','overview']):
        tool = 'summary'
    else:
        return {'answer':'Local analytics supports sports, peak hours, equipment issues, departments, years, trends, top students, fines and totals. Please ask about one of these.','tool':'none','data':None,'trace':[], 'mode':'local_rules'}
    data = _run_tool(tool, 30, db)
    if not data:
        answer = 'No matching records were found.'
    elif tool == 'by_sport':
        top = max(data, key=lambda row: row['count'])
        answer = f"{top['sport'].replace('_',' ').title()} has the most bookings: {top['count']}."
    elif tool == 'equipment_issues':
        field = 'lost_count' if 'lost' in text else 'damaged_count'
        count = max(row[field] for row in data)
        names = ', '.join(row['equipment_name'] for row in data if row[field] == count)
        answer = f"{names}: {count} recorded {'losses' if field == 'lost_count' else 'damage incidents'}." if count else 'No matching equipment incidents are recorded.'
    elif tool == 'peak_hours':
        top = max(data, key=lambda row: row['count'])
        answer = f"The busiest recorded hour is {int(top['hour']):02}:00, with {top['count']} bookings."
    else:
        answer = 'Results from the recorded data: ' + json.dumps(data, ensure_ascii=False) + '.'
    events = []
    trace.record({'trace':events}, 'local_query', 'completed', f'Keyword routing selected {tool}; no external model call.', start, tool=tool)
    return {'answer':answer, 'tool':tool, 'data':data, 'trace':events, 'mode':'local_rules'}
