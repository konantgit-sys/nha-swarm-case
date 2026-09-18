#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""СБОР ДАННЫХ ДЛЯ ИССЛЕДОВАНИЯ: хронология, метрики, вехи.

Каждые 15 минут снимаем состояние мира и наше и пишем строку в research/chronology.jsonl.
Когда метрика прыгает (колония закрыта, артефакт взят, очки выросли, новая кража),
дописываем веху в research/CHRONICLE.md — это будущий рассказ «как мы это сделали».
"""
import json
import os
import re
import time

import requests

BASE = '/home/agent/data/projects/nha'
RES = os.path.join(BASE, 'research')
B = 'https://nha.recluse.lol'
OURS = {149916: 'flint', 149917: 'onyx', 149918: 'topaz', 148956: 'v2bot', 149846: 'quartz',
        149942: 'm1', 149943: 'm2', 149961: 'f1', 149962: 'f2', 149963: 'f3',
        149987: 'g1', 149988: 'g2', 149990: 'g3', 149991: 'g4',
        149999: 'v1', 150000: 'v2', 150001: 'v3', 150002: 'v4', 150003: 'v5',
        148987: 'qwen', 150541: 'th1', 150542: 'th2', 150543: 'th3', 150544: 'th4', 150545: 'th5'}


def g(p):
    return requests.get(B + p, timeout=25).json()


def read_attunes():
    try:
        s = open(os.path.join(BASE, 'artifact_hunt.log'), errors='ignore').read()
    except Exception:
        return {}
    out = {}
    for m in re.finditer(r'(\d\d\.\d\d \d\d:\d\d:\d\d) \| (\w+)\s+ПРИВЯЗКА к (\w+): attuned', s):
        out[m.group(3)] = {'when': m.group(1), 'body': m.group(2)}
    return out


def theft_count():
    try:
        s = open(os.path.join(BASE, 'thieves.log'), errors='ignore').read()
    except Exception:
        return 0, {}, {}
    n, res, vic = 0, {}, {}
    for m in re.finditer(r'ОБЧИСТИЛ (.+?): stole (\d+) (\w+)', s):
        n += 1
        res[m.group(3)] = res.get(m.group(3), 0) + int(m.group(2))
        vic[m.group(1)] = vic.get(m.group(1), 0) + int(m.group(2))
    return n, res, vic


def main():
    os.makedirs(RES, exist_ok=True)
    w = g('/world')
    exp = g('/expansion').get('bodies') or {}
    st = g('/station')
    sc = g('/scene')
    rec = g('/records')
    try:
        ms = (g('/milestones') or {}).get('milestones') or []
    except Exception:
        ms = []
    me = g('/observe/148956').get('inventory') or {}
    q = g('/observe/148987').get('inventory') or {}
    n, res, vic = theft_count()
    cols = {k: '%s/%s' % ((v.get('colony') or {}).get('modules_done'), (v.get('colony') or {}).get('modules_total'))
            for k, v in exp.items()}
    row = {
        'ts': int(time.time()), 'when': time.strftime('%d.%m %H:%M'), 'tick': w.get('tick'),
        'era': w.get('era'),
        'trunk': sum(v for v in me.values() if isinstance(v, (int, float))),
        'metal': me.get('metal'), 'chip': me.get('chip'), 'titanium': me.get('titanium'),
        'composite': me.get('composite'), 'nanohematite': me.get('nanohematite'),
        'qwen_credits': q.get('credits'),
        'thefts': n, 'theft_value': sum({'chip': 60, 'motor': 40, 'crystal': 11, 'copper': 6,
                                         'metal': 3, 'wood': 1}.get(k, 1) * v for k, v in res.items()),
        'theft_res': res, 'theft_victims': vic,
        'colonies': cols, 'station_done': sum(1 for m in (st.get('modules') or []) if m.get('complete')),
        'station_total': len(st.get('modules') or []),
        'attunes': read_attunes(),
        'rich_agent': (rec.get('richest') or {}).get('name'),
        'agents_online': sum(1 for a in sc['agents'] if a.get('online')),
        'milestones': len(ms),
        'ats': [{'who': m.get('name'), 'kind': (m.get('data') or {}).get('kind'),
                 'tick': m.get('tick'), 'first': (m.get('data') or {}).get('first')}
                for m in ms if m.get('kind') == 'attune'][:8],
    }
    hist = os.path.join(RES, 'chronology.jsonl')
    prev = None
    if os.path.exists(hist):
        with open(hist) as f:
            lines = f.readlines()
        if lines:
            try:
                prev = json.loads(lines[-1])
            except Exception:
                pass
    with open(hist, 'a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')

    # вехи
    marks = []
    if prev:
        if row['thefts'] > prev.get('thefts', 0):
            marks.append('кражи: %d → %d (+%d единиц, ~%s кр)' % (
                prev.get('thefts', 0), row['thefts'], sum(res.values()),
                sum({'chip': 60}.get(k, 1) * v for k, v in res.items())))
        if len(row['attunes']) > len(prev.get('attunes') or {}):
            new = set(row['attunes']) - set(prev.get('attunes') or {})
            marks.append('АРТЕФАКТ: привязан %s телом %s' % (
                ', '.join(new), ', '.join(row['attunes'][k]['body'] for k in new)))
        for k, v in row['colonies'].items():
            if v != (prev.get('colonies') or {}).get(k) and v.split('/')[0] > \
                    str((prev.get('colonies') or {}).get(k, '0/0')).split('/')[0]:
                marks.append('КОЛОНИЯ %s: %s → %s' % (k, (prev.get('colonies') or {}).get(k), v))
        if (row['station_done'] or 0) > (prev.get('station_done') or 0):
            marks.append('СТАНЦИЯ: модулей готово %s' % row['station_done'])
        if row['qwen_credits'] and prev.get('qwen_credits'):
            d = row['qwen_credits'] - prev['qwen_credits']
            if abs(d) > 3000:
                marks.append('КАССА Qwen %+d кредитов (эскроу/продажи)' % d)
    with open(os.path.join(RES, 'CHRONICLE.md'), 'a') as f:
        for m in marks:
            f.write('- **%s** (тик %s) — %s\n' % (row['when'], row['tick'], m))
    print('записано. вех: %d. трюм %s, краж %s, колонии %s' % (len(marks), row['trunk'], n, cols))


if __name__ == '__main__':
    main()
