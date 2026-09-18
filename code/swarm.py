#!/usr/bin/env python3
"""swarm.py — единая оркестрация тел: у каждого своя постоянная роль.
Цикл по крону: каждый прогон берёт ОЧЕРЕДНУЮ ПАРТИЮ тел (движок обрабатывает ~1 интент за тик ~35 с,
поэтому 17 тел разом = перегруз очереди). Ротация хранится в swarm_state.json.

Роли:
  miner   — добывает свой ресурс (железо/алюминий/кремний/сера/нефть/кислота), сам летит к жиле
  builder — строит монументы/зиккураты на свободной земле (очки изобретений)
  trader  — держит sell-заявки по живому топ-биду (правило: бид не ниже лучшего аска)
  scout   — уходит в дальний квадрат искать артефакты (attune = +1 добыча навсегда)
"""
import sys, json, os, time, random

sys.path.insert(0, '/home/agent/data/projects/nha')
import newbot

BASE = '/home/agent/data/projects/nha'
STATE = os.path.join(BASE, 'swarm_state.json')
LOG = os.path.join(BASE, 'swarm.log')
BATCH = int(os.environ.get('SWARM_BATCH', '6'))
DL = 18

ROLES = {
    'g1': ('miner', 'iron'), 'g2': ('miner', 'aluminum'), 'g3': ('miner', 'silicon'),
    'g4': ('miner', 'iron'), 'm1': ('miner', 'iron'), 'm2': ('miner', 'silicon'),
    'onyx': ('miner', 'aluminum'), 'topaz': ('miner', 'iron'), 'f3': ('miner', 'silicon'),
    'flint': ('miner', 'sulfur'), 'f1': ('miner', 'oil'), 'f2': ('miner', 'acid'),
    'v1': ('miner', 'sulfur'), 'v2': ('miner', 'oil'), 'v3': ('miner', 'acid'),
    'v4': ('scout', ''), 'v5': ('builder', ''),
}


def line(s):
    with open(LOG, 'a') as f:
        f.write(time.strftime('%d.%m %H:%M:%S | ') + s + '\n')


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {'i': 0}


def mine_role(bot, res):
    o = bot.obs()
    alt = o.get('altitude') or 0
    if alt > 100:
        return bot.call('land', {}, dl=DL)
    d = o.get('nearby_deposits') or []
    live = [x for x in d if (x.get('amount') or 0) > 0]
    tgt = next((x for x in live if x.get('resource') == res), None) or (live[0] if live else None)
    if tgt is None:
        return 'нет жил рядом — жду'
    if (tgt.get('dist') or 99) <= 1:
        return bot.call('mine', {'resource': tgt['resource'], 'n': 60}, dl=DL)
    return bot.call('move', {'x': tgt['x'], 'y': tgt['y']}, dl=DL)


def builder_role(bot, _):
    o = bot.obs()
    inv = o.get('inventory') or {}
    if (o.get('altitude') or 0) > 100:
        return bot.call('land', {}, dl=DL)
    # монумент/зиккурат на свободной земле = очки изобретений и след в мире
    for shape in ('ziggurat', 'monument', 'pyramid'):
        if (inv.get('metal') or 0) >= 30 and (inv.get('carbon') or 0) >= 10:
            return bot.call('construct', {'shape': shape}, dl=DL)
    d = o.get('nearby_deposits') or []
    live = [x for x in d if (x.get('amount') or 0) > 0]
    if live:
        t = live[0]
        return bot.call('mine' if (t.get('dist') or 9) <= 1 else 'move',
                        {'resource': t['resource'], 'n': 40} if (t.get('dist') or 9) <= 1 else {'x': t['x'], 'y': t['y']}, dl=DL)
    return 'нет жил — жду'


def scout_role(bot, _):
    o = bot.obs()
    if (o.get('altitude') or 0) > 100:
        return bot.call('land', {}, dl=DL)
    art = o.get('artifacts') or []
    if art:
        a = art[0]
        d = abs(a['x'] - (o.get('position') or [0, 0])[0]) + abs(a['y'] - (o.get('position') or [0, 0])[1])
        return bot.call('attune', {}) if d <= 1 else bot.call('move', {'x': a['x'], 'y': a['y']}, dl=DL)
    # идём в дальний неисследованный угол
    x, y = random.randint(10, 220), random.randint(10, 220)
    return bot.call('move', {'x': x, 'y': y}, dl=DL)


def trader_role(bot, _):
    o = bot.obs()
    inv = o.get('inventory') or {}
    goods = [('motor', 40), ('insulated_wire', 20), ('alloy', 14), ('crystal', 11), ('plastic', 10)]
    for r, price in goods:
        if (inv.get(r) or 0) > 5:
            return bot.call('order', {'side': 'sell', 'resource': r, 'qty': min(10, inv[r]), 'price': price}, dl=DL)
    return 'нечего продавать'


def main():
    st = load_state()
    names = list(ROLES)
    batch = [names[(st['i'] + k) % len(names)] for k in range(BATCH)]
    st['i'] = (st['i'] + BATCH) % len(names)
    json.dump(st, open(STATE, 'w'))
    for n in batch:
        role, res = ROLES[n]
        try:
            bot = newbot.load(n)
            fn = {'miner': mine_role, 'builder': builder_role, 'scout': scout_role, 'trader': trader_role}[role]
            r = fn(bot, res)
            line('%-6s %-8s %-9s %s' % (n, role, res, str(r)[:88]))
        except Exception as e:
            line('%-6s %-8s ОШИБКА %s' % (n, role, str(e)[:70]))


if __name__ == '__main__':
    main()
