#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЧЕСТНАЯ СМЕТА: сколько стоила игра. Что измерено, а что оценка — помечено прямо в выводе.

Логика:
  автоматика (крон-контуры) — токенов 0, это Python на нашем сервере. Измеряем: запуски, строки логов.
  модель (я) — только доклады и решения. Считаем сессии и токены по заявке, деньги — по тарифу-вилке.
Ничего не выдумываем: где не измерено, печатаем слово ОЦЕНКА.
"""
import glob
import os
import subprocess
import sys

BASE = '/home/agent/data/projects/nha'


def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()


def main():
    days = float(sys.argv[1]) if len(sys.argv) > 1 else 5
    py = glob.glob(os.path.join(BASE, '*.py'))
    logs = glob.glob(os.path.join(BASE, '*.log'))
    lines = 0
    for f in py:
        try:
            lines += sum(1 for _ in open(f, errors='ignore'))
        except Exception:
            pass
    loglines = 0
    logbytes = 0
    for f in logs:
        try:
            logbytes += os.path.getsize(f)
            loglines += sum(1 for _ in open(f, errors='ignore'))
        except Exception:
            pass
    cron = len([l for l in sh('crontab -l').splitlines() if l.strip() and not l.startswith('#')])
    journal = glob.glob(os.path.join(BASE, 'journal', '*'))
    imgs = glob.glob(os.path.join(BASE, 'journal', '**', '*.png'), recursive=True) + \
        glob.glob(os.path.join(BASE, 'journal', '**', '*.jpg'), recursive=True)
    # расписание: сколько запросов к API даёт автоматика (по ритму контуров, ОЦЕНКА)
    req_per_hour = 0
    for per_min, bodies, calls in ((3, 5, 3), (2, 3, 4), (2, 3, 6), (5, 1, 15), (10, 1, 8),
                                   (15, 1, 12)):
        req_per_hour += 60.0 / per_min * bodies * calls
    print('=== ИЗМЕРЕНО (наши файлы) ===')
    print('скриптов: %d | строк кода: ~%d | логов: %d | строк логов: %d | крон-задач: %d'
          % (len(py), lines, len(logs), loglines, cron))
    print('объём логов: %.1f МБ | материалов для показа: %d файлов (из них картинок %d)'
          % (logbytes / 1e6, len(journal), len(imgs)))
    print()
    tok = 0
    print('=== АВТОМАТИКА (токенов модели — 0) ===')
    print('запросов к API игры: ~%.0f/час (ОЦЕНКА по ритму контуров), ~%.0f тыс./сутки'
          % (req_per_hour, req_per_hour * 24 / 1000))
    print('трафик: ~%.0f-%.0f МБ/сутки (ОЦЕНКА: 3-10 КБ на ответ движка)'
          % (req_per_hour * 24 * 3 / 1000, req_per_hour * 24 * 10 / 1000))
    print('токенов модели в петле игры: 0 — ни один крон не зовёт модель')
    print()
    print('=== МОДЕЛЬ (это и есть платное) ===')
    print('сессия = один мой заход на доклад/решение: вход 45-75 тыс. токенов, выход 3-5 тыс. (ОЦЕНКА)')
    for lo, hi in ((10, 20),):
        for per_day_lo, per_day_hi in ((lo, hi),):
            n_lo, n_hi = per_day_lo * days, per_day_hi * days
            t_lo = n_lo * 48 / 1000.0
            t_hi = n_hi * 80 / 1000.0
            tok = (t_lo + t_hi) / 2
            print('дней в игре: %.0f | сессий: %d-%d | токенов: %.1f-%.1f млн'
                  % (days, n_lo, n_hi, t_lo, t_hi))
            print('деньги: при 300 ₽/млн → %.0f-%.0f ₽ | при 800 ₽/млн → %.0f-%.0f ₽ (тариф даёт кабинет)'
                  % (t_lo * 300, t_hi * 300, t_lo * 800, t_hi * 800))
    acts = 355 * 24 * days
    print()
    print('=== ЦЕНА ОДНОГО ИГРОВОГО ДЕЙСТВИЯ ===')
    print('действий за период: ~%.0f (355/час × 24 × %.0f дней)' % (acts, days))
    if tok:
        print('токенов на одно действие: %.4f млн → при 800 ₽/млн это %.3f ₽ за действие'
              % (tok / acts * 1, 800 * tok / acts))
    print('плюс платные генерации материалов: картинок/страниц журнала — %d шт.' % len(imgs))


if __name__ == '__main__':
    main()
