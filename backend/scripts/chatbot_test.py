"""
Chatbot behaviour suite.

Sends industrial and non-industrial prompts to the live API and checks that the
system behaves honestly in both cases: grounded answers with real citations for
in-domain questions, and an explicit refusal (never a confident invention) for
questions the indexed corpus cannot support.

Usage:  python chatbot_test.py [base_url] [routing_mode]
"""

import json
import sys
import textwrap
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000').rstrip('/')
MODE = sys.argv[2] if len(sys.argv) > 2 else 'LOCAL'
API = f'{BASE}/api/v1'

INDUSTRIAL = [
    'What is the maximum discharge pressure for PUMP-101?',
    'Explain the maintenance history of PUMP-101.',
    'Are there conflicting pressure values?',
    'Which SOP should be followed before startup?',
    'What safety warnings exist for PSV-330?',
    'Which documents support your answer about PUMP-101 pressure?',
]

GENERAL = [
    'Tell me a joke.',
    'What is quantum computing?',
    'Who won the FIFA World Cup?',
    'Write Python code to reverse a string.',
    'Explain recursion.',
    'What is machine learning?',
]


def ask(question: str) -> dict:
    request = urllib.request.Request(
        f'{API}/query/submit',
        data=json.dumps({'query': question, 'routing_mode': MODE, 'session_id': 'behaviour-suite'}).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode('utf-8', 'replace'))


def summarise(question: str, payload: dict) -> dict:
    return {
        'question': question,
        'agent': payload['reasoning_path'][-1] if payload['reasoning_path'] else '-',
        'score': payload['confidence_score'],
        'band': payload['confidence_band'],
        'citations': len(payload['citations']),
        'graph': payload['confidence_metadata'].get('graph_verified'),
        'engine_id': 'ollama' if 'Ollama' in payload['engine'] else 'other',
        'grounded': payload['grounded'],
        'answer': payload['response'],
        'sources': sorted({c['filename'] for c in payload['citations']}),
        'trace_steps': len(payload['decision_replay_path']),
        'memory_events': len(payload['organizational_memory']['past_actions']),
    }


print(f'\nRouting mode: {MODE}   Endpoint: {API}\n')
print('=' * 92)
print('INDUSTRIAL PROMPTS — expect grounded answers with real citations')
print('=' * 92)

industrial_results = []
for question in INDUSTRIAL:
    result = summarise(question, ask(question))
    industrial_results.append(result)
    print(f"\nQ: {question}")
    print(f"   agent={result['agent']}  score={result['score']}% {result['band']}  "
          f"cites={result['citations']}  graph={result['graph']}  steps={result['trace_steps']}")
    if result['sources']:
        print(f"   sources: {', '.join(s[:38] for s in result['sources'])}")
    print(textwrap.indent(textwrap.fill(result['answer'][:300], 84), '   | '))

print('\n' + '=' * 92)
print('GENERAL PROMPTS — expect honest refusal, never a confident invention')
print('=' * 92)

general_results = []
for question in GENERAL:
    result = summarise(question, ask(question))
    general_results.append(result)
    print(f"\nQ: {question}")
    print(f"   agent={result['agent']}  score={result['score']}% {result['band']}  "
          f"cites={result['citations']}  grounded={result['grounded']}")
    print(textwrap.indent(textwrap.fill(result['answer'][:260], 84), '   | '))

# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------
print('\n' + '=' * 92)
print('BEHAVIOUR CHECKS')
print('=' * 92)

failures = []


def verify(label: str, ok: bool, detail: str = '') -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f'   {detail}' if detail and not ok else ''))
    if not ok:
        failures.append(f'{label} :: {detail}')


grounded_industrial = [r for r in industrial_results if r['citations'] > 0]
verify('industrial questions retrieve real sources',
       len(grounded_industrial) >= 5,
       f'{len(grounded_industrial)}/6 produced citations')

verify('at least one industrial answer is graph-corroborated',
       any(r['graph'] for r in industrial_results))

verify('industrial answers cite only real indexed documents',
       all(s.endswith('.pdf') or 'Graph' in s for r in industrial_results for s in r['sources']),
       str([s for r in industrial_results for s in r['sources']])[:160])

verify('no industrial answer claims 100% certainty',
       all(r['score'] <= 95.0 for r in industrial_results))

verify('every industrial answer carries an execution trace',
       all(r['trace_steps'] >= 3 for r in industrial_results))

verify('maintenance question surfaced real history',
       any(r['memory_events'] > 0 for r in industrial_results))

# General prompts must never be answered with confident fabricated citations.
verify('general questions produce no fabricated citations',
       all(r['citations'] == 0 or r['score'] < 50 for r in general_results),
       str([(r['question'][:26], r['citations'], r['score']) for r in general_results]))

verify('general questions do not claim strong evidence',
       all(r['band'] not in ('HIGH',) for r in general_results),
       str([(r['question'][:26], r['band']) for r in general_results]))

refusal_markers = (
    'could not find', 'not map to', "don't", 'do not', 'no supporting',
    'not contain', 'unable', 'no information', 'not available', 'industrial',
)
verify('general answers redirect rather than answer from model memory',
       all(any(marker in r['answer'].lower() for marker in refusal_markers) for r in general_results),
       str([(r['question'][:26], r['answer'][:70]) for r in general_results if not any(
           m in r['answer'].lower() for m in refusal_markers)])[:400])

print('\n' + '=' * 92)
print(f'  {len(failures)} failure(s)')
for failure in failures:
    print(f'   - {failure}')
print('=' * 92)
sys.exit(1 if failures else 0)
