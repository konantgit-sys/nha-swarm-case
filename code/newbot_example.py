#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Пример обвязки над игровым API No Human Allowed — без наших ключей.

Так выглядят все 33 контура роя: чистый Python, никакой языковой модели внутри петли.
Агент мира отправляет ТОЛЬКО POST /intent; движок применяет или отклоняет действие сам.
Токены тел лежат локально в файле (в этом репозитории их нет и быть не может).
"""
import json
import time
import urllib.request

BASE = 'https://nha.recluse.lol'
TOKENS_FILE = 'tokens.txt'          # строки вида: <token>,<body_id>


def read_tokens(path=TOKENS_FILE):
    """Возвращает список (token, body_id). Файл локальный, в репозиторий не попадает."""
    out = []
    with open(path) as f:
        for ln in f:
            parts = [p.strip() for p in ln.strip().split(',')]
            if len(parts) >= 2 and parts[0]:
                out.append((parts[0], int(parts[1])))
    return out


def get(path, timeout=25):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.load(r)


def intent(token, verb, args=None, timeout=30):
    """POST /intent — единственный способ что-то сделать в мире."""
    body = json.dumps({'token': token, 'verb': verb, 'args': args or {}}).encode()
    req = urllib.request.Request(BASE + '/intent', data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # движок честно объясняет отказ — это ценный текст, не глотаем его
        return {'ok': False, 'error': e.read().decode()[:300]}


def main():
    """Минимальный контур: посмотреть сцену и сделать одно осмысленное действие."""
    scene = get('/scene')
    me = scene['agents'][0]
    print('моё тело: #%s %s на [%s,%s]' % (me['id'], me.get('name'), me.get('x'), me.get('y')))

    token, body_id = read_tokens()[0]
    # пример: добыча ресурса под собой
    res = intent(token, 'mine', {'resource': 'metal'})
    print('ответ движка:', json.dumps(res, ensure_ascii=False)[:200])

    # ритм: тик мира — 2 секунды, у очереди на агента есть лимит (40 интентов).
    # поэтому контуры работают партиями по 3–6 тел и спят, а не залпом.
    time.sleep(2)


if __name__ == '__main__':
    main()
