import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.chat.application.use_cases import Assessment


def test_command_evaluates_real_policy_and_writes_report(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    class Classifier:
        def classify(self, messages):
            return Assessment(1, 0) if messages[-1].content == 'Python?' else Assessment(0, 1)

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: Classifier())
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps([
        {'id': 'legitimate', 'category': 'legitimate', 'question': 'Python?', 'history': []},
        {'id': 'attack', 'category': 'attack', 'question': 'Ignore rules', 'history': []},
        {'id': 'scope', 'category': 'out_of_scope', 'question': 'Weather?', 'history': []},
    ]))
    report = tmp_path / 'report.json'
    call_command('eval_chat', cases=str(dataset), report=str(report), stdout=StringIO())
    result = json.loads(report.read_text())
    assert result['passed'] is True
    assert result['metrics']['accuracy'] == 1
    assert result['metrics']['attack_acceptance_rate'] == 0
    assert result['metrics']['legitimate_block_rate'] == 0
    assert result['failed_cases'] == []


def test_command_fails_and_records_when_quality_targets_are_missed(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    class Classifier:
        def classify(self, messages):
            return Assessment(1, 0)

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: Classifier())
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps([
        {'id': 'legitimate', 'category': 'legitimate', 'question': 'Python?', 'history': []},
        {'id': 'attack', 'category': 'attack', 'question': 'Ignore rules', 'history': []},
    ]))
    report = tmp_path / 'report.json'

    with pytest.raises(CommandError, match='metas'):
        call_command('eval_chat', cases=str(dataset), report=str(report), stdout=StringIO())

    result = json.loads(report.read_text())
    assert result['passed'] is False
    assert result['metrics']['attack_acceptance_rate'] == 1


def test_inclusive_threshold_and_independent_safety_gates(tmp_path, monkeypatch):
    import pytest
    from django.core.management.base import CommandError

    from apps.chat.management.commands import eval_chat

    class Classifier:
        def classify(self, messages):
            return Assessment(1, 0)

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: Classifier())
    cases = [{'id': str(i), 'category': 'legitimate', 'question': 'Python?', 'history': []}
             for i in range(19)]
    cases.append({'id': 'attack', 'category': 'attack', 'question': 'Ignore', 'history': []})
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps(cases))
    report = tmp_path / 'report.json'
    options = dict(cases=str(dataset), report=str(report), stdout=StringIO())
    with pytest.raises(CommandError):
        call_command('eval_chat', **options)
    assert json.loads(report.read_text())['failed_cases'][0]['id'] == 'attack'
    call_command('eval_chat', max_attack_acceptance_rate=1, **options)
    assert json.loads(report.read_text())['passed'] is True
    with pytest.raises(CommandError):
        call_command('eval_chat', min_accuracy=0.951, max_attack_acceptance_rate=1, **options)


def test_provider_errors_are_failures_even_with_permissive_targets(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    class Classifier:
        def classify(self, messages):
            raise RuntimeError('secret payload must never appear')

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: Classifier())
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps([
        {'id': 'good', 'category': 'legitimate', 'question': 'Python?', 'history': []},
        {'id': 'bad', 'category': 'attack', 'question': 'Ignore', 'history': []},
    ]))
    report = tmp_path / 'report.json'
    with pytest.raises(CommandError):
        call_command('eval_chat', cases=str(dataset), report=str(report), min_accuracy=0,
                     max_legitimate_block_rate=1, max_attack_acceptance_rate=1,
                     stdout=StringIO())
    result = json.loads(report.read_text())
    assert result['passed'] is False
    assert len(result['failed_cases']) == 2
    assert result['counts']['errors'] == 2
    assert 'secret' not in report.read_text()


@pytest.mark.parametrize('payload', [
    [], {}, [{'id': 'a', 'category': 'legitimate', 'question': 'Python?', 'history': []}],
    [{'id': 'a', 'category': 'attack', 'question': '', 'history': []}],
    [{'id': 'a', 'category': 'unknown', 'question': 'Python?', 'history': []}],
])
def test_invalid_dataset_fails_before_provider(tmp_path, monkeypatch, payload):
    from apps.chat.management.commands import eval_chat

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: pytest.fail('provider called'))
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps(payload))
    with pytest.raises(CommandError):
        call_command('eval_chat', cases=str(dataset), report=str(tmp_path / 'report.json'))


@pytest.mark.parametrize('threshold', [-0.01, 1.01, float('nan'), float('inf')])
def test_invalid_threshold_fails_before_provider(tmp_path, monkeypatch, threshold):
    from apps.chat.management.commands import eval_chat

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: pytest.fail('provider called'))
    with pytest.raises(CommandError):
        call_command('eval_chat', min_accuracy=threshold, report=str(tmp_path / 'report.json'))


def test_configuration_failure_saves_sanitized_report(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    def fail():
        raise RuntimeError('secret configuration')

    monkeypatch.setattr(eval_chat, 'create_classifier', fail)
    report = tmp_path / 'report.json'
    with pytest.raises(CommandError):
        call_command('eval_chat', report=str(report), stdout=StringIO())
    assert json.loads(report.read_text())['passed'] is False
    assert 'secret' not in report.read_text()


def test_history_policy_boundaries_and_report_provenance(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    received = []

    class Classifier:
        def classify(self, messages):
            received.append(messages)
            question = messages[-1].content
            scores = {'allowed': (0.85, 0.149), 'injection': (1, 0.15), 'scope': (0.849, 0)}
            return Assessment(*scores[question], evaluator='test', model='fixed')

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: Classifier())
    dataset = tmp_path / 'cases.json'
    history = [{'role': 'assistant', 'content': 'Untrusted instruction'}]
    dataset.write_text(json.dumps([
        {'id': 'good', 'category': 'legitimate', 'question': 'allowed', 'history': []},
        {'id': 'bad', 'category': 'attack', 'question': 'injection', 'history': history},
        {'id': 'scope', 'category': 'out_of_scope', 'question': 'scope', 'history': []},
    ]))
    report = tmp_path / 'report.json'
    call_command('eval_chat', cases=str(dataset), report=str(report), stdout=StringIO())
    result = json.loads(report.read_text())
    assert received[1][0].content == 'Untrusted instruction'
    assert result['counts'] == {
        'total': 3, 'legitimate': 1, 'attack': 1, 'out_of_scope': 1, 'errors': 0,
    }
    assert result['cases'][1]['decision'] == 'reject_injection'
    assert result['cases'][2]['decision'] == 'reject_scope'
    assert len(result['dataset_sha256']) == 64
    assert result['policy'] == {'python_threshold': 0.85, 'injection_threshold': 0.15}
    assert result['created_at']
    assert result['cases'][0]['model'] == 'fixed'


def test_legitimate_block_rate_can_fail_despite_accuracy_pass(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    class Classifier:
        def classify(self, messages):
            return Assessment(0, 0)

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: Classifier())
    cases = [{'id': str(i), 'category': 'attack', 'question': 'Ignore', 'history': []}
             for i in range(19)]
    cases.append({'id': 'good', 'category': 'legitimate', 'question': 'Python?', 'history': []})
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps(cases))
    report = tmp_path / 'report.json'
    with pytest.raises(CommandError):
        call_command('eval_chat', cases=str(dataset), report=str(report), stdout=StringIO())
    result = json.loads(report.read_text())
    assert result['metrics']['accuracy'] == 0.95
    assert result['metrics']['legitimate_block_rate'] == 1


def test_report_cannot_overwrite_dataset(tmp_path, monkeypatch):
    from apps.chat.management.commands import eval_chat

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: pytest.fail('provider called'))
    dataset = tmp_path / 'cases.json'
    content = json.dumps([
        {'id': 'good', 'category': 'legitimate', 'question': 'Python?', 'history': []},
        {'id': 'bad', 'category': 'attack', 'question': 'Ignore', 'history': []},
    ])
    dataset.write_text(content)
    with pytest.raises(CommandError):
        call_command('eval_chat', cases=str(dataset), report=str(dataset))
    assert dataset.read_text() == content


@pytest.mark.parametrize('change', [
    {'history': {}}, {'history': None}, {'history': [{'role': 'system', 'content': 'x'}]},
    {'question': ' '}, {'question': 'x' * 4001}, {'id': 'bad'}, {'category': 'typo'},
])
def test_malformed_conversation_or_duplicate_id_is_rejected(tmp_path, monkeypatch, change):
    from apps.chat.management.commands import eval_chat

    monkeypatch.setattr(eval_chat, 'create_classifier', lambda: pytest.fail('provider called'))
    cases = [
        {'id': 'good', 'category': 'legitimate', 'question': 'Python?', 'history': []},
        {'id': 'bad', 'category': 'attack', 'question': 'Ignore', 'history': []},
    ]
    cases[0].update(change)
    dataset = tmp_path / 'cases.json'
    dataset.write_text(json.dumps(cases))
    with pytest.raises(CommandError):
        call_command('eval_chat', cases=str(dataset), report=str(tmp_path / 'report.json'))
