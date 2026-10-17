# ShotLock — consistency checking for short-drama storyboards

English | [中文](./README_CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](./shotlock)

A structured spec and a zero-dependency checking engine for short-drama shot lists.

LLMs write plausible shots one at a time and fall apart when you put them together. The lead has long hair in scene 5 and short hair in scene 17. The two speakers swap screen sides between cuts. Three seconds of screen time carries sixty characters of dialogue nobody can voice in time. ShotLock turns those failures into fifteen checkable rules.

## Sponsors

Slots open. ShotLock is MIT and stays free — sponsoring buys visibility, not influence. Rates and terms: [SPONSORING.md](./SPONSORING.md).

<!-- Lead / Service / Supporting slots go here as they are sold. -->

---

## Why another tool

Three things already exist, and none of them do this:

| Approach | What it gives you | Problem |
|---|---|---|
| Prose outline | A readable breakdown | Not machine-checkable. Nothing catches the drift |
| Spreadsheet template | A consistent shape | Checks that cells are filled, not that the story holds together |
| LLM self-review | "Looks consistent to me" | The model reviewing its own output misses the same things it missed while writing, because it still only sees one shot at a time |

ShotLock separates the two jobs: **the model writes content, the script enforces continuity.** Characters and scenes are declared once in a table; every shot references them by id; the engine verifies the references never drift.

## Quick start

No install step, no dependencies beyond the standard library:

```bash
git clone https://github.com/nianjiang888/shotlock.git
cd shotlock
python -m shotlock examples/good_deck.json
```

```
==============================================================
ShotLock consistency report — 夜班便利店 · episode 1
==============================================================
5 shots · 2 characters · 1 scene
Total 13.9s / target 14.0s

Verdict: PASS
Blocking 0 · Major 0 · Minor 0   0 issues
==============================================================
```

Exit codes: `0` pass, `1` blocking-level issues found, `2` bad input, `3` internal error. That makes it usable as a gate in a generation pipeline.

Other output:

```bash
python -m shotlock deck.json --html report.html   # self-contained HTML, printable to PDF
python -m shotlock deck.json --json result.json   # structured output
python -m shotlock deck.json --fail-on P1         # treat major issues as failures too
python -m shotlock deck.json --only SL003,SL008   # run specific rules
python -m shotlock deck.json --skip SL015         # skip a rule
```

## The rules

Fifteen rules across three levels. Full table and the reasoning behind the thresholds: [references/RULES.md](./references/RULES.md).

- **P0 blocking** — `SL001` structure, `SL002` shot duration, `SL003` speech rate, `SL006` character registration, `SL007` scene registration
- **P1 major** — `SL004` appearance drift, `SL005` scene continuity, `SL008` axis crossing, `SL009` duration budget, `SL010` transition abuse
- **P2 minor** — `SL011` shot-size rhythm, `SL012` emotion monotony, `SL013` subtitle length, `SL014` prop flicker, `SL015` establishing shot

Three of them carry the project:

**SL003 speech rate.** Chinese dialogue over 7.5 characters per second cannot be voiced cleanly with emotion. The lower bound is 2.2, not 3.0 — an early build used 3.0 and flagged perfectly normal shots, because five characters over two seconds is ordinary performance pacing, not dragging.

**SL008 axis crossing.** Two or more shared characters flipping screen side together between adjacent cuts in the same scene. Skipped when the previous shot is a wide, since a wide resets the axis. This is the rule models fail most often, because a model generating shot *n* never sees where anyone stood in shot *n-1*.

**SL011 shot-size rhythm.** Only fires at four or more identical sizes in a row, because shot-reverse-shot is legitimately three close-ups back to back. Escalates to major when the average shot runs over 3.5s — fast cutting on one size is a style, long takes on one size is just dull.

## Gallery

Both reports come from the bundled examples, so you can reproduce them exactly:

| | |
|---|---|
| [examples/good_deck.json](./examples/good_deck.json) | [report](./gallery/good_report.html) — clean, 0 issues |
| [examples/bad_deck.json](./examples/bad_deck.json) | [report](./gallery/bad_report.html) — 15 planted violations, one per rule |

The bad deck is deliberately broken and annotated with what each shot violates. It exists so you can see every rule fire rather than reading about it.

## Use it as an agent skill

ShotLock ships with [SKILL.md](./SKILL.md), so it also works as a skill inside Claude Code, Cursor, Codex, and Copilot. The loop is: declare entities → generate shots → run the check → fix → re-run until P0 is clear.

Installing it as a skill is what makes the checker useful rather than decorative, because the model can then run the loop itself instead of you pasting JSON back and forth.

## Documentation

- [ShotSpec v0.1](./references/SHOT_SPEC.md) — every field, enum and constraint
- [Rules](./references/RULES.md) — full rule table and threshold rationale
- [SKILL.md](./SKILL.md) — the agent workflow

## Contributing

Rules are the interesting part, and the best ones come from real failures. See [CONTRIBUTING.md](./CONTRIBUTING.md) — the short version is: describe the failure you actually hit, then propose the rule that would have caught it.

## Related project

ShotLock checks storyboards; it doesn't write them. For the other half of the chain: [Mojinge](https://www.mojinge.cloud/?utm_source=github_shotlock&utm_medium=readme&utm_campaign=shotlock_v01) (mojinge.cloud) turns a story into a shootable screenplay — one sentence in, episode breakdowns, character/scene/prop assets and per-shot prompts out. Import a novel and it runs the full adaptation pass: story hub, episode outline, adapted script, shot list. Pay per run, not per month.

## License

MIT. See [LICENSE](./LICENSE).
