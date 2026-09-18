#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ОХОТА ЗА АРТЕФАКТАМИ (найдено чтением движка, не догадками).

Три артефакта в мире (/scene -> artifacts), у каждого свой бонус:
  resonant_monolith  -> yield_buff=1 : +50% НАВСЕГДА на каждой добыче (и только 1 тело в мире может привязаться)
  gravity_lens       -> lens_until   : вдвое дешевле взлёт на 200 тиков
  stasis_relic       -> stasis=3     : 3 заряда, пропускают орбитальный распад
Первый, кто вообще привяжется к артефакту в этом мире, берёт +200 очков, остальные +60.
Привязка = команда attune, стоя на расстоянии <= 1 по манхэттену.
"""
import json
import os
import sys
import time

import requests

import newbot

BASE = '/home/agent/data/projects/nha'
B = 'https://nha.recluse.lol'
LOG = os.path.join(BASE, 'artifact_hunt.log')
STATE = os.path.join(BASE, 'artifact_state.json')

BODIES = {
    'flint': 149916, 'onyx': 149917, 'topaz': 149918, 'me': 148956, 'quartz': 149846,
    'm1': 149942, 'm2': 149943, 'f1': 149961, 'f2': 149962, 'f3': 149963,
    'g1': 149987, 'g2': 149988, 'g3': 149990, 'g4': 149991,
    'v1': 149999, 'v2': 150000, 'v3': 150001, 'v4': 150002, 'v5': 150003,
    'qwen': 148987,
    'th1': 150541, 'th2': 150542, 'th3': 150543, 'th4': 150544, 'th5': 150545,
}


def line(s):
    msg = '%s | %s' % (time.strftime('%d.%m %H:%M:%S'), s)
    with open(LOG, 'a') as f:
        f.write(msg + '\n')
    print(msg, flush=True)


def get(path):
    return requests.get(B + path, timeout=25).json()


def bot(tag):
    tok = open(os.path.join(BASE, 'tokens', tag + '.txt')).read().strip()
    return newbot.Bot(BODIES[tag], tok)


def main():
    sc = get('/scene')
    arts = [a for a in (sc.get('artifacts') or []) if a.get('loc') == 'ground']
    if not arts:
        line('артефактов в сцене нет')
        return
    pos = {a['id']: a for a in sc.get('agents', [])}
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}

    DONE = st.setdefault('_done', {})      # {'kind:x:y': [теги, которые уже привязаны]}
    FULL = st.setdefault('_full', [])      # артефакты, где слотов больше нет
    CAP = {'resonant_monolith': 1, 'gravity_lens': 3, 'stasis_relic': 3}
    taken = set()
    for t in DONE.values():
        taken |= set(t)
    for art in arts:
        key = '%s:%s:%s' % (art['kind'], art['x'], art['y'])
        if key in FULL or len(DONE.get(key, [])) >= CAP.get(art['kind'], 1):
            continue
        tag = st.get(key)
        if tag in DONE.get(key, []):
            tag = None
        if tag not in BODIES or BODIES[tag] not in pos:
            cands = sorted(
                (abs(pos[i]['x'] - art['x']) + abs(pos[i]['y'] - art['y']), t, i)
                for t, i in BODIES.items() if i in pos and t not in taken
            )
            if not cands:
                continue
            _, tag, _ = cands[0]
            st[key] = tag
            taken.add(tag)
        me = pos[BODIES[tag]]
        d = abs(me['x'] - art['x']) + abs(me['y'] - art['y'])
        alt = me.get('alt') or 0
        try:
            b = bot(tag)
            if d <= 1 and alt <= 0:
                res = b.call('attune')
                line('%-6s ПРИВЯЗКА к %s: %s' % (tag, art['kind'], res[:110]))
                if 'already fully attuned' in str(res).lower() and key not in FULL:
                    FULL[key] = True
                    st['_full'] = sorted(FULL)
                    json.dump(st, open(STATE, 'w'))
                    line('%-6s СТОП: %s занят полностью — снимаю с целей' % (tag, art['kind']))

                if 'already attuned' in res or 'applied' in res:
                    DONE.setdefault(key, []).append(tag)   # слот наш — этим телом больше не дёргаем
                    st.pop(key, None)
                if 'fully attuned' in res:
                    FULL.append(key)
                    st.pop(key, None)
            elif 'no artifact' in res if False else alt > 0:
                res = b.call('land')
                line('%-6s снижаюсь к %s (alt %s): %s' % (tag, art['kind'], alt, res[:80]))
            else:
                res = b.call('move', {'x': art['x'], 'y': art['y']})
                line('%-6s → %s [%s,%s] d=%d: %s' % (tag, art['kind'], art['x'], art['y'], d, res[:60]))
        except Exception as e:
            line('%-6s ОШИБКА %s' % (tag, str(e)[:90]))
    json.dump(st, open(STATE, 'w'))


if __name__ == '__main__':
    main()   # блокировку держит cron (flock -n), внутри дублировать нельзя — иначе сам себя не пустит
