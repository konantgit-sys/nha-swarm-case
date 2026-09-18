#!/usr/bin/env python3
"""thieves.py — ОТРЯД ВОРОВ (v2b-th1..v2b-th5). Обучение и доктрина рейда.

МЕХАНИКА (вскрыта в движке engine.py, строки 2003-2035):
  · steal возможен ТОЛЬКО вплотную (шахматная дистанция <= 1) и только у агента
  · THEFT_COOLDOWN = 12 тиков (~24 с) — и на вора, и на ЖЕРТВУ (robbed_recent).
    Значит пятерых воров надо разводить по РАЗНЫМ целям, а не бить толпой одного.
  · шанс = 45% минус vigilance жертвы (мин 10%, макс 80%). Каждая кража поднимает
    vigilance жертвы -> повторно обчищать одного и того же всё труднее.
  · берём не больше 8 единиц за раз, но не больше held//4
  · кредиты украсть НЕЛЬЗЯ («credits cannot be stolen») — только ресурсы и loose parts
  · если заметили (шанс ~25%) -> wanted_until = +60 тиков (~2 мин): вор «в розыске»,
    поэтому после грязной кражи обязан уйти и отлежаться
  · нельзя бить: союзников, новичков под защитой, только что возродившихся, лежачих
  · краденое отдаём в центральный склад обменом (trade) — обмен работает на расстоянии

РОЛИ ПО ЦЕЛЯМ (разводим по разным жертвам):
  th1 -> создатель       th2 -> топ-киты       th3 -> топ-киты
  th4 -> все, кто богат  th5 -> все, кто богат
"""
import sys, json, os, time, random, urllib.request

sys.path.insert(0, '/home/agent/data/projects/nha')
import newbot

BASE = '/home/agent/data/projects/nha'
LOG = BASE + '/thieves.log'
HOST = 'https://nha.recluse.lol'
BATCH = int(os.environ.get('TH_BATCH', '2'))
DL = 16
MAIN = 148956                      # центральный склад — я
OWN = ('v2b', 'v2bot', 'shroud', 'qwen')       # своих не трогаем
ALLY = ('shroud',)


# ПРИКАЗ: каждому вору — свой кит. Профиль = что именно брать (по цене и пользе для нашего склада)
TARGETS = {
    'v2b-th1': (139606, 'Roman Recluse (АВТОР ИГРЫ)', ['crystal', 'titanium', 'silicon', 'copper']),
    'v2b-th2': (142748, 'MonkeyGang (топ мира)', ['chip', 'crystal', 'titanium', 'lens']),
    'v2b-th3': (3152,   'Trader (НПС автора)', ['motor', 'insulated_wire', 'alloy', 'iridium']),
    'v2b-th4': (143848, 'vanish glados (топ мира)', ['iridium', 'titanium', 'crystal', 'chip']),
    'v2b-th5': (25570,  'to4ka (топ мира)', ['motor', 'alloy', 'insulated_wire', 'lens']),
}

# то же, без привязки к конкретному вору (для справки)
PRIORITY = {
    139606: 'Roman Recluse (автор игры)',
    142748: 'MonkeyGang (топ)',
    137841: 'Prospector (НПС создателя)',
    3160: 'Miner (НПС создателя)',
    25570: 'to4ka (топ)',
    3392: 'KimiClaw (топ)',
    3152: 'Trader (НПС создателя)',
    3108: 'Barbarian (варлорд)',
}
# что стоит красть в первую очередь (цена бида в книге депо)
VALUE = ['motor', 'insulated_wire', 'alloy', 'crystal', 'iridium', 'titanium',
         'plastic', 'glass', 'chip', 'copper', 'silver', 'gold', 'lens']


def _state(tag):
    try:
        return json.load(open(BASE + '/thief_%s.json' % tag))
    except Exception:
        return {}


def _save(tag, d):
    json.dump(d, open(BASE + '/thief_%s.json' % tag, 'w'))


def line(s):
    with open(LOG, 'a') as f:
        f.write(time.strftime('%d.%m %H:%M:%S | ') + s + '\n')


def load_thieves():
    d = json.load(open(BASE + '/thieves.json'))
    return {n: newbot.Bot(v['id'], v['token']) for n, v in d.items()}


def fetch(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode())


def world_map():
    """id -> (name, x, y) по всему миру"""
    try:
        return {a['id']: (a.get('name') or '', a['x'], a['y']) for a in fetch(HOST + '/map').get('agents') or []}
    except Exception:
        return {}


def pick_loot(victim_id):
    """выбираем, что взять: сначала дорогое, иначе самое объёмное"""
    try:
        inv = fetch(HOST + '/observe/%d' % victim_id).get('inventory') or {}
    except Exception:
        return None, None
    for r in VALUE:
        if int(inv.get(r) or 0) >= 4:
            return r, int(inv[r])
    bulk = {k: int(v) for k, v in inv.items()
            if isinstance(v, (int, float)) and int(v) >= 4 and k != 'credits'
            and k not in ('o2', 'co2', 'steam')}
    if not bulk:
        return None, None
    r = max(bulk, key=lambda k: bulk[k])
    return r, bulk[r]


def hand_over(bot, resource, n):
    """краденое — в центральный склад обменом (работает на расстоянии)"""
    try:
        r = str(bot.call('trade', {'to': MAIN, 'give': {resource: n}, 'want': {}}))
        return r[:58]
    except Exception as e:
        return 'обмен не прошёл: ' + str(e)[:40]


def duty(tag, bot):
    o = bot.obs()
    i = o.get('inventory') or {}
    pos = o.get('position') or [0, 0]
    hp = o.get('hp') or 0
    st = _state(tag)
    noticed = int(st.get('noticed') or 0)
    wanted = noticed and (time.time() - noticed) < 150      # ~2 мин в розыске после грязной кражи
    # 1) в розыске — уходим от места преступления и лежим тихо
    if wanted:
        return 'в розыске — отхожу и отлёживаюсь', bot.call('move', {'x': pos[0] + random.choice([-5, 5]), 'y': pos[1] + random.choice([-5, 5])}, dl=DL)
    # 2) подлечиться
    if hp and hp < 40:
        med = o.get('medicines') or {}
        return 'лечусь', bot.call('heal', {'with': 'medkit' if med.get('medkit') else 'salve'}, dl=DL)
    # 3) выбираем цель
    mp = world_map()
    # СВОЯ цель по приказу; если её нет в живой карте — ищем рядом
    tid, tname, tres = TARGETS.get(tag, (None, None, []))
    if tid and tid in mp:
        nm, x, y = mp[tid]
        d = max(abs(x - pos[0]), abs(y - pos[1]))
        if d > 1:
            return '%s → иду к %s d=%d' % (tag, tname, d), bot.call('move', {'x': x, 'y': y}, dl=DL)
        # добежали: берём свой профиль, если пусто — что подороже
        inv = fetch(HOST + '/observe/%d' % tid).get('inventory') or {}
        tries = 0
        for r in tres:
            if tries >= 2:
                break
            if int(inv.get(r) or 0) >= 4:
                tries += 1
                out = bot.call('steal', {'from': tid, 'resource': r}, dl=DL)
                sres = str(out)
                if 'stole' in sres and 'failed' not in sres:
                    got = int(sres.split('stole ')[1].split()[0])
                    _save(tag, {'noticed': int(time.time())} if 'noticed' in sres else {})
                    return 'ОБЧИСТИЛ %s: stole %d %s → %s' % (tname, got, r, hand_over(bot, r, got)), out
                if 'noticed' in sres:
                    _save(tag, {'noticed': int(time.time())})
                return 'попытка у %s (%s): %s' % (tname, r, sres[:70]), out
        return '%s: в профиле пусто' % tname, None
    if tid:
        return '%s → цели нет на карте, жду' % tag, None
    cands = []
    for aid, who in PRIORITY.items():
        if aid not in mp:
            continue
        nm, x, y = mp[aid]
        if any(k in nm.lower() for k in OWN + ALLY):
            continue
        d = abs(x - pos[0]) + abs(y - pos[1])
        cands.append((d, aid, nm, x, y))
    for aid, (nm, x, y) in mp.items():
        if aid in PRIORITY or any(k in nm.lower() for k in OWN + ALLY) or not nm:
            continue
        d = abs(x - pos[0]) + abs(y - pos[1])
        if d <= 40:
            cands.append((d, aid, nm, x, y))
    if not cands:
        return 'целей рядом нет', None
    cands.sort()
    off = (list(load_thieves()).index(tag) if tag in load_thieves() else 0) % 3
    if len(cands) > 1:
        cands = cands[off:] + cands[:off]        # каждый вор бьёт СВОЮ жертву, иначе robbed_recent блокирует второго
    d, aid, nm, x, y = cands[0]
    # 4) подойти вплотную и взять
    if max(abs(x - pos[0]), abs(y - pos[1])) > 1:
        return 'иду к %s (#%d) d=%d' % (nm[:14], aid, d), bot.call('move', {'x': x, 'y': y}, dl=DL)
    res, held = pick_loot(aid)
    if not res:
        return '%s пуст — ищу другого' % nm[:14], None
    out = bot.call('steal', {'from': aid, 'resource': res}, dl=DL)
    got = 0
    s = str(out)
    if 'stole' in s and 'failed' not in s:
        try:
            got = int(s.split('stole ')[1].split()[0])
        except Exception:
            got = 0
    if 'noticed' in s:
        st['noticed'] = int(time.time()); _save(tag, st)
    elif got:
        st.pop('noticed', None); _save(tag, st)
    if got:
        ho = hand_over(bot, res, got)
        return 'ОБЧИСТИЛ %s: stole %d %s → склад: %s' % (nm[:14], got, res, ho), out
    return 'попытка у %s(%s) — %s' % (nm[:14], res, s[:70]), out


def main():
    th = load_thieves()
    names = list(th)
    st = {'i': 0}
    try:
        st = json.load(open(BASE + '/thieves_state.json'))
    except Exception:
        pass
    batch = [names[(st['i'] + k) % len(names)] for k in range(BATCH)]
    st['i'] = (st['i'] + BATCH) % len(names)
    json.dump(st, open(BASE + '/thieves_state.json', 'w'))
    for n in batch:
        try:
            what, res = duty(n, th[n])
            line('%-8s %s' % (n, what))
        except Exception as e:
            line('%-8s ОШИБКА %s' % (n, str(e)[:80]))


if __name__ == '__main__':
    main()
