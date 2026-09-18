# План публикации кейса NHA — стратегия по фазам

Цель: закрепиться вокруг мира No Human Allowed как **самый активный и полезный разработчик**,
показать платформу V2Bot и GitHub Антона, и сделать это так, чтобы автору игры было приятно,
а не обидно. Значит: сначала ценность (данные, находки, честные баг-репорты), потом реклама.

Правило работы: **внешнее публичное действие — только после «публикуй»**. Всё, что внутри наших
аккаунтов, делаю сразу.

---

## Фаза 0. Доступы и инвентарь — СДЕЛАНО 18.09 23:30

```
ключ GitHub: найден локально, аккаунт konantgit-sys (Anton Konovalov), 20 публичных репозиториев
права: repo, workflow, admin:repo_hook, write:packages, notifications, project, user
лимит API: 5000/5000
инвентарь материалов: презентация кейса (10 слайдов, PDF), Журнал №1 (9,7 МБ), ТРИЗ-разбор (12 МБ),
   research/CHRONICLE.md, metrics.jsonl, DOCTRINE.md, 8 очищенных скриптов контуров
проверка секретов: в публикуемые файлы ключи и токены не попадают (проверено, 0 попаданий)
```

## Фаза 1. Кейс-репозиторий у себя — ДЕЛАЮ СЕЙЧАС

`github.com/konantgit-sys/nha-swarm-case` — публичный, MIT.
Содержимое: README-кейс (RU + EN), код контуров без ключей, DOCTRINE.md, lessons.md,
research/ (хронология и каркас исследования), deck/ (презентация).
Зачем: одна ссылка, которую можно дать автору игры, в чат, в профиль — и по которой всё проверяемо.

## Фаза 2. Страница-кейс на нашем домене

Поддомен вида `nha-case.v2.site`: тот же кейс, но красиво и с картинками — цифры, таймлайн,
схема четырёх слоёв, честный блок про провалы, ссылки (игра, репозиторий игры, наш GitHub, V2Bot).
Проверка: `curl` даёт 200 и правильный контент, а не обещание.

## Фаза 3. Официальный фидбек автору — тексты готовы, ЖДУ «публикуй»

Шесть issues в `github.com/Recluse/nha-mmo` (там сейчас 0 открытых — мы будем первыми, и это
должно выглядеть как подарок, а не как захват). Репозиторий англоязычный — тексты на английском.
Все с воспроизведением, без эмоций, без рекламы в теле. Подпись нейтральная: «swarm of 25 bodies».

**1. `attune` events are invisible in /feed**
Title: `Attunement events missing from /feed (visible only in /milestones)`
Body: We attuned two artefacts at ticks 1554204 and 1554603. The events appear in /milestones but never
in /feed, so agents that follow /feed cannot learn that an artefact slot got taken. Expected: attune
events in /feed, or a documented note that artefact state is milestones-only.

**2. No way to know artefact slot occupancy before travelling**
Title: `Expose artefact slot occupancy (slots_total / slots_taken)`
Body: Three bodies travelled 24–106 tiles to three artefacts. Two arrived to `this artifact is already
fully attuned`. There is no endpoint that shows remaining slots, so the trip cost is wasted by design.
Request: `slots_total` / `slots_taken` in /map or /scene for artefacts, or an `attuned_by` list.

**3. Intent queue limit is documented only in AGENTS.md**
Title: `Document the 40-intent queue limit in /rules (or serve it via API)`
Body: The 40-intent-per-agent queue limit is stated in AGENTS.md but not returned by /rules or any
endpoint. An agent that only reads the API concludes the world is slow, not that it is throttled.
Request: expose the limit and current queue depth.

**4. `order` returns "bad order" without the offending field**
Title: `order errors do not identify the invalid field`
Body: POST /intent with verb=order and `side` omitted returns `bad order`. It cost us several minutes to
find that `side` must be `buy` or `sell`. Request: return which field failed, e.g. `missing: side`.

**5. /milestones is a 40-entry window dominated by destroyed events**
Title: `Add a kind filter to /milestones (or pagination)`
Body: With 40 entries, world events like attune/invent get pushed out within hours by `destroyed`.
Request: `?kind=` filter or `?before=` pagination so agents can build reliable timelines.

**6. Polling load: an SSE/WebSocket state stream would replace ~35k requests/day**
Title: `Consider a push stream for world state (SSE) to reduce polling load`
Body: A swarm of 25 bodies polling state every few seconds generates ~35k requests/day from one client.
A single SSE stream (or a `since_tick` delta endpoint) would cut that by an order of magnitude and
remove most of the load our swarm adds to your server. Happy to test it.

## Фаза 4. Закрепление в игре как разработчик

- Одно короткое сообщение в чат игры: благодарность автору, ссылка на кейс, без реферальных
  вставок в лоб. Спам в игровом чате убивает репутацию быстрее, чем приносит переходы.
- Полезность для других агентов: поставки ресурсов контрактом (единственный легальный канал
  передачи кредитов), публичные ориентиры по ценам, помощь молодым телам.
- Игровые цели: Титан (нужны три фондера — проходим только роем), свободные слоты артефактов,
  удержание первого места изобретателя.
- Мы уже в истории мира: три привязки к артефактам и изобретения подписаны `v2bot-agent`.

## Фаза 5. Данные и вторая волна

- Журнал №3: статистика `metrics.jsonl` по дням (трюм, касса, кражи, вехи), схема 33 контуров,
  карта решений и ошибок.
- Обновить профиль GitHub (README профиля): закрепить кейс, дать ссылку на платформу.
- Если автор ответит на issues — публичный разбор ответа в кейсе: это и есть «дружить»,
  а не кричать о себе.

## Фаза 6. Держим на карандаше (уже работает)

- `watch_author.py` каждые 10 минут: issues и коммиты игры, звёзды, милстоуны, чат,
  состояние наших тел и трюма, первое место изобретателя → сигналы в `SIGNALS.md`.
- Доклады по сигналу: 11:00 и 21:00. Тихо — одна строка, без спама.
