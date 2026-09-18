#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ПРОВЕРЯЮЩИЙ КОНТУР: автоматизм делает, я проверяю и лечу.

Каждые 5 минут смотрим по каждому отряду: свежий ли лог, есть ли ошибки, был ли результат.
Лечим сами: пропавшую крон-строку вернём, мёртвый цикл дёрнем руками, зацикленное тело снимем с цели.
Результат пишем в verify.log и digest.md — по нему я и докладываю.
"""
import json
import os
import re
import subprocess
import time

BASE = '/home/agent/data/projects/nha'
PY = '/usr/bin/python3'
REPAIR = {
    'swarm': 'cd %s && flock -n /tmp/swarm.lock timeout 150 python3 swarm.py >> swarm_cron.log 2>&1',
    'thieves': 'cd %s && flock -n /tmp/thieves.lock timeout 150 python3 thieves.py >> thieves_cron.log 2>&1',
    'artifact_hunt': 'cd %s && flock -n artifact_hunt.lock timeout 100 python3 artifact_hunt.py >> artifact_cron.log 2>&1',
    'shield_watch': 'cd %s && flock -n /tmp/shield.lock timeout 150 python3 shield_watch.py >> shield_watch_cron.log 2>&1',
    'telemetry': 'cd %s && timeout 90 python3 telemetry.py >> telemetry_cron.log 2>&1',
    'collect': 'cd %s && timeout 90 python3 collect.py >> collect_cron.log 2>&1',
}
LOOPS = {
    'swarm':         ('swarm.log', 25, '*/3 * * * * flock -n /tmp/swarm.lock timeout 170 /usr/bin/python3 /home/agent/data/projects/nha/swarm.py >> /home/agent/data/projects/nha/swarm_cron.log 2>&1'),
    'thieves':       ('thieves.log', 20, '*/2 * * * * flock -n /tmp/thieves.lock timeout 170 /usr/bin/python3 /home/agent/data/projects/nha/thieves.py >> /home/agent/data/projects/nha/thieves_cron.log 2>&1'),
    'artifact_hunt': ('artifact_hunt.log', 15, '*/2 * * * * flock -n /home/agent/data/projects/nha/artifact_hunt.lock timeout 110 python3 /home/agent/data/projects/nha/artifact_hunt.py >> /home/agent/data/projects/nha/artifact_cron.log 2>&1'),
    'shield_watch':  ('shield_watch.log', 20, '*/5 * * * * flock -n /tmp/shield.lock timeout 170 /usr/bin/python3 /home/agent/data/projects/nha/shield_watch.py >> /home/agent/data/projects/nha/shield_watch_cron.log 2>&1'),
    'telemetry':     ('metrics.jsonl', 30, '*/10 * * * * cd /home/agent/data/projects/nha && timeout 100 python3 telemetry.py >> telemetry_cron.log 2>&1'),
    'collect':       ('research/chronology.jsonl', 40, '*/15 * * * * cd /home/agent/data/projects/nha && timeout 110 python3 collect.py >> collect_cron.log 2>&1'),
}
BAD = re.compile(r'Traceback|ОШИБКА|Exception|rejected|loop detected|timeout', re.I)


def age_min(path):
    if not os.path.exists(path):
        return 10 ** 6
    return (time.time() - os.path.getmtime(path)) / 60.0


def cron_lines():
    return subprocess.run(['crontab', '-l'], capture_output=True, text=True).stdout


def tail_lines(path, n=400):
    try:
        with open(path, errors='ignore') as f:
            return f.readlines()[-n:]
    except Exception:
        return []


def main():
    cur = cron_lines()
    report, healed, problems = [], [], []
    for name, (logf, maxage, cron) in LOOPS.items():
        path = os.path.join(BASE, logf)
        a = age_min(path)
        state = 'ok'
        if cron.split(' ')[0] not in cur or logf not in cur:
            if cron not in cur:
                subprocess.run('(crontab -l; echo "%s") | crontab -' % cron, shell=True)
                healed.append(name + ': крон-строка возвращена')
        if a > maxage:
            state = 'stale'
            cmd = REPAIR.get(name)
            if cmd:
                subprocess.Popen(cmd % BASE, shell=True)
            healed.append('%s: лог молчит %.0f мин → дёрнул цикл руками' % (name, a))
        # считаем только СВЕЖИЕ ошибки (за 30 минут) — старые не должны пугать вечно
        cutoff = time.time() - 1800
        bad = []
        for l in tail_lines(path):
            m = re.match(r'(\d\d)\.(\d\d) (\d\d):(\d\d):(\d\d)', l)
            if not m:
                continue
            d, mo, H, M, S = map(int, m.groups())
            ts = time.mktime((time.localtime().tm_year, mo, d, H, M, S, 0, 0, -1))
            if ts >= cutoff - 86400 and BAD.search(l):
                bad.append(l.strip())
        if len(bad) > 8:
            problems.append('%s: %d подозрительных строк, пример: %s' % (name, len(bad), bad[-1][:90]))
        report.append('%-13s %-6s лог %.1f мин назад' % (name, state, a))

    # тела: кто упал, кто зациклился
    try:
        import urllib.request
        sc = json.load(urllib.request.urlopen('https://nha.recluse.lol/scene', timeout=20))
        ours = {149916, 149917, 149918, 148956, 149846, 149942, 149943, 149961, 149962, 149963,
                149987, 149988, 149990, 149991, 149999, 150000, 150001, 150002, 150003, 148987,
                150541, 150542, 150543, 150544, 150545}
        down = [a['id'] for a in sc['agents'] if a['id'] in ours and a.get('downed')]
        if down:
            problems.append('лежат (downed): %s' % down)
        report.append('тел в сцене наших: %d из 25' % sum(1 for a in sc['agents'] if a['id'] in ours))
    except Exception as e:
        problems.append('сцена не ответила: %s' % str(e)[:60])

    txt = ['VERIFY %s' % time.strftime('%d.%m %H:%M')] + report
    if healed:
        txt.append('ЛЕЧИЛ: ' + '; '.join(healed))
    if problems:
        txt.append('ВНИМАНИЕ: ' + '; '.join(problems))
    out = '\n'.join(txt)
    with open(os.path.join(BASE, 'verify.log'), 'a') as f:
        f.write(out + '\n\n')
    with open(os.path.join(BASE, 'digest.md'), 'w') as f:
        f.write('```\n' + out + '\n```\n')
    print(out)


if __name__ == '__main__':
    main()
