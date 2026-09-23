"""Read labeled synthetic conversations before constructing external clients."""
import json
from pathlib import Path

from apps.chat.application.use_cases import Message, validate_history, validate_text

CATEGORIES = {'legitimate', 'attack', 'out_of_scope'}


def read_cases(path, limits):
    cases = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(cases, list) or not cases:
        raise ValueError('Conjunto vazio ou inválido.')
    for case in cases:
        validate_case(case, limits)
    validate_coverage(cases)
    return cases


def validate_coverage(cases):
    ids = [case['id'] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('IDs duplicados.')
    categories = {case['category'] for case in cases}
    if not {'legitimate', 'attack'} <= categories:
        raise ValueError('Inclua casos legítimos e ataques.')


def validate_case(case, limits):
    if not isinstance(case, dict) or set(case) != {'id', 'category', 'question', 'history'}:
        raise ValueError('Campos inválidos.')
    validate_text(case['id'], 100)
    if case['category'] not in CATEGORIES:
        raise ValueError('Categoria inválida.')
    validate_text(case['question'], limits.question)
    history = read_history(case['history'])
    validate_history(history, limits)
    if len(case['question']) + sum(len(item.content) for item in history) > limits.total:
        raise ValueError('Conversa excede limite total.')


def read_history(history):
    if not isinstance(history, list):
        raise ValueError("Histórico deve ser lista.")
    return [Message(**message) for message in history]
