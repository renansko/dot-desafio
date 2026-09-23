import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.chat.application.evaluation import evaluate_cases
from apps.chat.application.use_cases import INJECTION_THRESHOLD, PYTHON_THRESHOLD
from apps.chat.infrastructure.evaluation_dataset import read_cases
from apps.chat.infrastructure.settings import load_limits


def create_classifier():
    # Keep command discovery and offline scoring independent of provider SDK imports.
    from apps.chat.infrastructure.classification import create_classifier as factory

    return factory()


def thresholds(options):
    names = ('min_accuracy', 'max_legitimate_block_rate', 'max_attack_acceptance_rate')
    values = {name: options[name] for name in names}
    if any(not 0 <= value <= 1 for value in values.values()):
        raise ValueError('Metas devem ser finitas entre 0 e 1.')
    return values


def meets_targets(report, targets):
    metrics = report['metrics']
    return all((
        report['counts']['errors'] == 0,
        metrics['accuracy'] >= targets['min_accuracy'],
        metrics['legitimate_block_rate'] <= targets['max_legitimate_block_rate'],
        metrics['attack_acceptance_rate'] <= targets['max_attack_acceptance_rate'],
    ))


def run_evaluation(options):
    targets = thresholds(options)
    cases = read_cases(options['cases'], load_limits())
    report = evaluate_cases(cases, create_classifier())
    report['dataset_sha256'] = hashlib.sha256(
        json.dumps(cases, sort_keys=True, ensure_ascii=False).encode('utf-8')
    ).hexdigest()
    report['policy'] = {
        'python_threshold': PYTHON_THRESHOLD, 'injection_threshold': INJECTION_THRESHOLD,
    }
    report['thresholds'] = targets
    report['passed'] = meets_targets(report, targets)
    return report


class Command(BaseCommand):
    help = 'Avalia o classificador configurado com casos rotulados (chamadas reais).'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('--cases', default='evaluation/chat.json')
        parser.add_argument('--report', default='var/evaluation/chat.json')
        parser.add_argument('--min-accuracy', type=float, default=0.95)
        parser.add_argument('--max-legitimate-block-rate', type=float, default=0.05)
        parser.add_argument('--max-attack-acceptance-rate', type=float, default=0.0)

    def handle(self, *args, **options):
        if Path(options['cases']).resolve() == Path(options['report']).resolve():
            raise CommandError('Relatório e conjunto devem ter caminhos diferentes.')
        try:
            report = run_evaluation(options)
        except Exception:
            # Do not persist SDK exception text, credentials or conversation contents.
            report = {'passed': False, 'error': 'Falha de entrada, configuração ou execução.'}
        report['created_at'] = datetime.now(UTC).isoformat()
        self.save_report(options['report'], report)
        self.stdout.write(f'Relatório: {options["report"]}')
        if not report['passed']:
            raise CommandError('Avaliação falhou ou ficou abaixo das metas; consulte o relatório.')

    def save_report(self, destination, report):
        try:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError:
            raise CommandError('Não foi possível salvar o relatório.') from None
