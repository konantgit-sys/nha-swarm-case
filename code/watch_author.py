#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""СТОРОЖ РЕАКЦИИ: держим на карандаше, что происходит с нами и вокруг нас.

Следит автономно, без модели:
  1. GitHub игры (Recluse/nha-mmo): новые issues, новые коммиты, звёзды, упоминания нас в тексте.
  2. Игра: новые милстоуны (особенно с нашими телами и чужие привязки к артефактам).
  3. Чат игры: новые сообщения + отдельный сигнал, если кого-то упомянули нас.
  4. Наши тела: лежит ли кто, не потеряли ли трюм (кража у нас), держим ли №1 изобретатель.
Важное пишет в SIGNALS.md — это то, о чём я докладываю первым делом.
"""
import json
import os
import re
import time

import requests

BASE = '/home/agent/data/projects/nha'
STATE = os.path.join(BASE, 'watch_state.json')
LOG = os.path.join(BASE, 'watch.log')
SIG = os.path.join(BASE, 'SIGNALS.md')
GH = 'https://api.github.com/repos/Recluse/nha-mmo'
B = 'https://nha.recluse.lol'
OURS = {149916, 149917, 149918, 148956, 149846, 149942, 149943, 149961, 149962, 149963,
        149987, 149988, 149990, 149991, 149999, 150000, 150001, 150002, 150003, 148987,
        150541, 150542, 150543, 150544, 150545}
US = re.compile(r'v2bot|v2b[-_]|v2b', re.I)


def line(path, m):
    with open(path, 'a') as f:
        f.write(time.strftime('%d.%m %H:%M:%S | ') + m + '\n')


def load():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def main():
    st = load()
    new_st = dict(st)
    signals = []

    # 1. GitHub игры
    try:
        r = requests.get(GH, timeout=20).json()
        if r.get('pushed_at') and r['pushed_at'] != st.get('gh_push'):
            cs = requests.get(GH + '/commits?per_page=3', timeout=20).json()
            if isinstance(cs, list) and cs:
                msg = (cs[0].get('commit') or {}).get('message', '').splitlines()[0][:110]
                signals.append('НОВЫЙ КОММИТ в игре: ' + msg)
                line(LOG, 'коммит: ' + msg)
            new_st['gh_push'] = r['pushed_at']
        if r.get('stargazers_count') != st.get('gh_stars'):
            signals.append('звёзды игры: %s → %s' % (st.get('gh_stars'), r.get('stargazers_count')))
            new_st['gh_stars'] = r.get('stargazers_count')
        iss = requests.get(GH + '/issues?state=all&per_page=10&sort=updated', timeout=20).json()
        if isinstance(iss, list):
            seen = set(st.get('gh_issues') or [])
            for it in iss:
                n = it.get('number')
                if n in seen:
                    continue
                who = (it.get('user') or {}).get('login')
                title = (it.get('title') or '')[:100]
                body = (it.get('body') or '')[:400]
                marks = ' МЕНЯЮТ НАС' if US.search(title + ' ' + body) else ''
                if st:
                    signals.append('ISSUE #%s от %s: %s (%s)%s'
                                   % (n, who, title, it.get('state'), marks))
                line(LOG, 'issue #%s %s | %s' % (n, who, title))
            new_st['gh_issues'] = [it.get('number') for it in iss]
    except Exception as e:
        line(LOG, 'github не ответил: ' + str(e)[:80])

    # 2. Милстоуны мира
    try:
        ms = (requests.get(B + '/milestones', timeout=25).json() or {}).get('milestones') or []
        top = ms[0]['id'] if ms else 0
        if st.get('ms_top') and top > st['ms_top'] and ms:
            for m in ms:
                if m['id'] <= st['ms_top']:
                    break
                d = m.get('data') or {}
                who = m.get('name') or '?'
                kind = d.get('kind') or m.get('kind')
                if str(who).lower().startswith('v2b') and st:
                    signals.append('наше событие: %s — %s' % (who, kind))
                else:
                    signals.append('чужое событие: %s — %s' % (who, kind))
                line(LOG, 'милстоун: %s %s' % (who, kind))
        new_st['ms_top'] = top
    except Exception as e:
        line(LOG, 'милстоуны: ' + str(e)[:60])

    # 3. Чат
    try:
        ch = requests.get(B + '/chat', timeout=25).json()
        msgs = ch.get('messages') or ch.get('chat') or []
        last = st.get('chat_last') or 0
        for m in msgs:
            if m.get('id', 0) > last:
                txt = m.get('text') or ''
                who = m.get('sender_name')
                if (US.search(txt) or US.search(str(who))) and st:
                    signals.append('В ЧАТЕ ПРО НАС: %s — %s' % (who, txt[:120]))
                if m.get('is_human') and st:
                    signals.append('ЧЕЛОВЕК В ЧАТЕ: %s — %s' % (who, txt[:120]))
        if msgs:
            new_st['chat_last'] = max(m.get('id', 0) for m in msgs)
    except Exception as e:
        line(LOG, 'чат: ' + str(e)[:60])

    # 4. Наши тела: лежат ли, воровали ли у нас, держим ли первое место
    try:
        sc = requests.get(B + '/scene', timeout=25).json()
        down = [a['id'] for a in sc['agents'] if a['id'] in OURS and a.get('downed')]
        if down:
            signals.append('ЛЕЖАТ НАШИ ТЕЛА: %s' % down)
        mine = [a for a in sc['agents'] if a['id'] == 148956]
        if mine and st.get('trunk'):
            cur = sum(v for v in (mine[0].get('inventory') or {}).values()
                      if isinstance(v, (int, float)))
            d = cur - st['trunk']
            if d < -500:
                signals.append('ТРЮМ УПАЛ: %s → %s (минус %s) — возможно, обчистили нас' % (st['trunk'], cur, -d))
            new_st['trunk'] = cur
        elif mine:
            new_st['trunk'] = sum(v for v in (mine[0].get('inventory') or {}).values()
                                  if isinstance(v, (int, float)))
        inv = (requests.get(B + '/records', timeout=25).json() or {}).get('top_inventor') or {}
        if inv.get('name') and inv['name'] != st.get('top_inv'):
            if st.get('top_inv'):
                signals.append('ИЗОБРЕТАТЕЛЬ №1 теперь %s (%s очков)' % (inv.get('name'), inv.get('pts')))
            new_st['top_inv'] = inv.get('name')
    except Exception as e:
        line(LOG, 'сцена: ' + str(e)[:60])

    json.dump(new_st, open(STATE, 'w'))
    if signals:
        with open(SIG, 'a') as f:
            for s in signals:
                f.write('- **%s** — %s\n' % (time.strftime('%d.%m %H:%M'), s))
        line(LOG, 'СИГНАЛОВ: %d' % len(signals))
        print('СИГНАЛОВ: %d' % len(signals))
        for s in signals:
            print('  •', s[:150])
    else:
        print('тихо: ничего нового')


if __name__ == '__main__':
    main()
