#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ТЕЛЕМЕТРИЯ И P&L: снимок метрик в metrics.jsonl + отчёт roi_report.txt.

Снимаем каждые 10 минут. Отчёт считает дельты (скорость), а не абсолюты:
сколько единиц/кредитов в час даёт экономика и сколько краж/единиц даёт криминал.
"""
import json
import os
import re
import time
from collections import Counter

import requests

BASE = '/home/agent/data/projects/nha'
B = 'https://nha.recluse.lol'
METRICS = os.path.join(BASE, 'metrics.jsonl')
REPORT = os.path.join(BASE, 'roi_report.txt')
BID = {'chip': 60, 'motor': 40, 'crystal': 11, 'copper': 6, 'metal': 3, 'wood': 1,
       'titanium': 10, 'iridium': 20, 'alloy': 14, 'lens': 5, 'insulated_wire': 20, 'plastic': 10}


def get(path):
    return requests.get(B + path, timeout=25).json()


def theft_stats():
    n, units, vic = 0, Counter(), Counter()
    try:
        for l in open(os.path.join(BASE, 'thieves.log'), errors='ignore'):
            m = re.search(r'ОБЧИСТИЛ (.+?): stole (\d+) (\w+)', l)
            if m:
                n += 1
                units[m.group(3)] += int(m.group(2))
                vic[m.group(1)] += int(m.group(2))
    except Exception:
        pass
    return n, units, vic


def snapshot():
    me = get('/observe/148956')
    inv = me.get('inventory') or {}
    q = get('/observe/148987').get('inventory') or {}
    exp = get('/expansion').get('bodies') or {}
    rec = get('/records')
    inv_pts = get('/inventors').get('leaderboard') or []
    n, units, vic = theft_stats()
    row = {
        'ts': int(time.time()),
        'when': time.strftime('%d.%m %H:%M'),
        'trunk': sum(v for k, v in inv.items() if isinstance(v, (int, float))),
        'chip': inv.get('chip'), 'crystal': inv.get('crystal'), 'metal': inv.get('metal'),
        'qwen_credits': q.get('credits'),
        'thefts': n,
        'theft_units': dict(units),
        'theft_value': sum(BID.get(k, 1) * v for k, v in units.items()),
        'top_victim': (max(vic.items(), key=lambda x: x[1])[0] if vic else None),
        'my_pts': next((a['pts'] for a in inv_pts if a['id'] == 148956), None),
        'richest': (rec.get('richest') or {}).get('name'),
        'colonies_done': sum(1 for d in exp.values() if (d.get('colony') or {}).get('complete')),
        'colonies_total': len(exp),
    }
    with open(METRICS, 'a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def report():
    rows = []
    try:
        for l in open(METRICS):
            try:
                rows.append(json.loads(l))
            except Exception:
                pass
    except Exception:
        pass
    if len(rows) < 2:
        return
    a, b = rows[0], rows[-1]
    h = max((b['ts'] - a['ts']) / 3600.0, 0.001)
    out = []
    out.append('P&L ЗА ПЕРИОД %s → %s (%.1f ч)' % (a['when'], b['when'], h))
    out.append('трюм:      %s → %s  (%+.0f ед/ч)' % (a['trunk'], b['trunk'], (b['trunk'] - a['trunk']) / h))
    out.append('кредиты:   %s → %s  (%+.0f кр/ч)' % (a['qwen_credits'], b['qwen_credits'],
                                                     (b['qwen_credits'] - a['qwen_credits']) / h))
    out.append('кражи:     %s → %s  (%+.1f краж/ч, %s единиц, ~%s кр по ставкам)' % (
        a['thefts'], b['thefts'], (b['thefts'] - a['thefts']) / h,
        b['theft_units'], b['theft_value']))
    out.append('очки:      %s (топ-1 изобретатель)' % b['my_pts'])
    out.append('колонии:   %s/%s готовы' % (b['colonies_done'], b['colonies_total']))
    out.append('самый богатый в мире: %s' % b['richest'])
    open(REPORT, 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    snapshot()
    report()
