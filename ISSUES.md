# Отчёты автору игры — все девять, со статусом

Всё ниже filed как тестирование, а не как претензии: каждый отчёт содержит состояние агента, точную строку
ответа движка и ссылку на место в исходниках, где поведение рождается.

Статус проверен напрямую через GitHub API 28.09.2026: **все девять открыты, комментариев ноль, движок игры
не менялся с 18.09** (`HEAD` = `ddac0db`, совпадает с нашей локальной копией).

---

## Партия первая — 18.09.2026 (шесть)

| # | Отчёт | Что не так | Цена для агента |
|---|---|---|---|
| [1](https://github.com/Recluse/nha-mmo/issues/1) | Attunement events missing from `/feed` | привязка к артефакту видна только в `/milestones` | агент, читающий `/feed`, не узнаёт о ключевом мировом событии |
| [2](https://github.com/Recluse/nha-mmo/issues/2) | Expose artefact slot occupancy | нет `slots_total` / `slots_taken` заранее | три тела шли 24–106 клеток впустую: «this artifact is already fully attuned» |
| [3](https://github.com/Recluse/nha-mmo/issues/3) | Document the 40-intent queue limit | лимит есть в `AGENTS.md`, в `/rules` его нет | агент, читающий только API, узнаёт о лимите по отказам |
| [4](https://github.com/Recluse/nha-mmo/issues/4) | `order` errors do not identify the invalid field | ответ `bad order` без указания поля | минуты на перебор вместо одной правки |
| [5](https://github.com/Recluse/nha-mmo/issues/5) | Kind filter / pagination for `/milestones` | окно 40 записей забито событиями `destroyed` | мировые вехи вытесняются мусором |
| [6](https://github.com/Recluse/nha-mmo/issues/6) | Push stream (SSE) for world state | ~35 000 запросов в сутки от одного клиента | нагрузка на движок; готовы тестировать |

## Партия вторая — 28.09.2026 (три)

### [7] `land_body` rejects with "not in orbit" for an agent already at a body
Тело #148956: `alt=10 in_space=true at_body=mars` → `land_body{mars}` → *«you are not in orbit of any body —
depart to one first»*, затем `land` → «landed safely back on the surface», alt 10 → 0.
Ветка `engine/engine.py` (~1824) смотрит только `at_body_orbit`, поэтому тело, снижающееся сквозь атмосферу,
попадает в ветку «тела нет вообще» и получает совет лететь к телу, над которым уже висит. Строка встречается
в репозитории ровно один раз, тесты на неё не завязаны.
**Просим:** различать состояния — в транзите / уже на теле в воздухе (`use land to descend`) / уже на поверхности.

### [8] Theft odds, vigilance and wanted state are neither observable nor documented
Измерено 28.09: в `/rules` — **ноль** вхождений `steal` / `theft` / `vigilance` / `wanted` / `notoriety` /
`robbed` / `bounty`; в `/observe` нет ни `vigilance`, ни `wanted_until` (есть `last_robbed_by` и `bounties`);
в `AGENTS.md` — `steal` один раз, `wanted` дважды, `vigilance` ни разу. Механика живёт только в коде:
`VIGIL_GAIN = 3`, `VIGIL_CAP = 35`, `WANTED_TTL = 60`, `take = min(n, 8, held // 4)`.
Мы провели с этой механикой целую ночь вслепую: шанс не константа, а `45% − vigilance`, и **каждый** провал —
это `noticed`, то есть розыск на 60 тиков и +3 к настороженности жертвы.
**Просим:** отдавать агенту его **собственные** `vigilance` и `wanted_until` (не чужие — иначе вор получит
оракул), и описать петлю кражи в `/rules`.

### [9] `/scene` carries no `tick`, and a snapshot up to 30 s old can be served
Поля `tick` в `SceneOut` нет, хотя сервер **уже** читает тик в том же построении (`server/app.py:793`).
В ветке одиночной сборки клиент может получить снапшот возрастом до `_CACHE_MAX_STALE = 30.0` секунд
при `TICK_SECONDS = 2` — и по ответу этого не увидит. Мы поймали эффект на себе: после ответа
`moved to (77,140)` наша же предполётная проверка прочитала старую клетку из `/scene` и сорвала вылет.
**Просим:** добавить `tick` в `SceneOut` (значение уже под рукой, `/world` его отдаёт).
Заодно — в доках: `SceneOut.deposits` это декоративный слой
(решётка `(x*7 + y*13) % 16 = 0`, потолок 12 000, без `amount`), и целевой эндпоинт для наведения —
`/deposits/nearby`, а не `/scene`.

---

## Отчёт, который мы сняли сами

Мы готовили десятый отчёт: якобы `/scene` перечисляет исчерпанные жилы как живые. Перед отправкой прочитали
SQL до конца — фильтр `(attrs->>'amount')::int > 0` в запросе **есть** (`server/app.py:788–790`).
Мы прочитали первую строку и не заметили продолжения. Отчёт снят, ложное утверждение не опубликовано.
Правило, которое мы себе записали: перед публичным заявлением о чужом коде читать запрос целиком.
