# Zombie Quest SideCharacter Update

Date: 2026-05-22

## New Trusted Constraint

SideCharacter's update changes the model:

```text
Gender Rerolling -> Zombifying -> ??? -> ???
```

Hard reading:

- Only one gender reroll is needed for the clean Zombie questline.
- Repeating gender rerolls to test M/F paths is likely wrong and may reset progress.
- The zombifying part is the same for everyone.
- The two later tasks are the same tasks for everyone, but their order can be randomized per player.
- Zombification amount is "50-ish"; 57 is too much, so test 50 and nearby lower values.
- Zombification targets are same gender as the post-reroll actor.
- Targets do not need to be unique and can be any race.

## Current Best Quest Shape

```text
1. Gender reroll exactly once.
2. After reroll, zombify same-gender targets through passive Blood Bar + manual grip.
3. Reach the real amount, most likely near 50.
4. Complete tail task A.
5. Complete tail task B.
```

The old `A/B/C` path model and the old 2x2 matrix with repeated gender rerolls are now deprecated. They were useful interpretations of the CSP hint before this update, but SideCharacter's message makes them reset-risk tests.

## Best Immediate Test

Pick the case matching the actor's post-reroll gender:

```text
CORE_M_50
CORE_F_50
```

Run:

```text
one gender reroll
-> same-gender passive Blood Bar
-> knock
-> manual grip
-> confirm zombie
-> repeat up to 50
```

During the same run, check progress at safe milestones:

```text
40, 45, 49, 50
```

Do not add commands, mode, race restrictions, a physical grid, or extra gender rerolls.

## Current Ranking For The Two Unknown Tasks

New image solve:

```text
BC  rule: char
xy  rule: mirror
bc  rule: gender
```

Interpretation:

- `xy` fits the gender-reroll / gender-axis part.
- `bc` fits same-gender B/C or gender-matched targets.
- `BC` under `char` plus the copied-appearance screenshot points to a character/appearance-copy condition.
- Items and accessories are still ruled out; this is about appearance/character state, not equipping cosmetics.

Updated ranking:

1. `CHAR_MIRROR`: copy/mirror character appearance, then same-gender zombification while that relation is active.
2. `PASSIVE_GRIP`: passive Blood Bar + manual grip may still be internally counted, but likely belongs to the zombifying phase.
3. `COUNT_ONLY`: the same-gender amount itself may complete the visible quest, and the "two tasks" may be hidden bookkeeping/order checks.
4. `T_G_BASE`: lower priority after the BC/xy/bc clue.
5. `X_C_BASE`: lower-priority base Zombie X/C fallback.
6. `COMMANDS`: very low priority because newer hints say commands are not needed and zombies do not act.

## Tail Simulation Result

The dedicated tail simulator was added after the `BC/xy/bc` solve and the copied-appearance screenshot.

Command:

```text
python zombie_test_runner.py --mode=simulate
```

Latest run:

```text
x50 count: 48.0%
x49 count: 25.0%
x45 count: 17.0%
x40 count: 10.0%

#1 Copy/mirror appearance, then same-gender final zombify: 55.8%
#2 B/C same-gender character mirror pair: 29.9%
#3 Copy appearance before count and keep it active: 12.5%
```

Best concrete reading for the last two-ish tasks:

```text
Tail A: copy or mirror another player's character appearance
Tail B: zombify/grip a same-gender target while that copied/mirrored relation is active
```

The second-best reading is the same idea as a state check:

```text
B/C same gender
plus B/C character appearance mirror/copy relation
```

So the correct tail is very likely `char + mirror + gender`, not items/accessories, commands, Volt/mode, or repeated gender rerolls.

## Toolchain Update

The Python runner was updated from the old 12-case A/B/C + 2x2 model to the new one-reroll model.

Useful commands:

```text
python zombie_test_runner.py --mode=csp
python zombie_test_runner.py --mode=list
python zombie_test_runner.py --mode=next
python zombie_test_runner.py --mode=report
python zombie_test_runner.py --mode=dispatch --max=4
python zombie_test_runner.py --mode=simulate
```

Verified on 2026-05-22:

- `py_compile` passed for all five modules.
- `--mode=csp` prints the updated one-reroll model.
- `--mode=list` generates updated core-count and tail-probe cases.
- `--mode=next` recommends `CORE_F_50` / `CORE_M_50` depending on post-reroll gender.
- `--mode=generate` writes `03_TOOLS/zombie_test_runner/all_test_cases.json`.
- `--mode=dispatch --max=4` writes task JSONs for the top four updated tests.
- `--mode=simulate` ranks the last two-ish tasks from all current hints and writes a report under `03_TOOLS/zombie_test_runner/reports/`.

## Current Best Answer

The quest is most likely:

```text
Gender reroll once
-> zombify about 50 same-gender players/targets
   using Zombie passive Blood Bar and manual grip
-> finish two hidden same-route checks
   most likely character-copy / mirror / gender checks:
   copy/mirror appearance + same-gender final zombify/check while active
```

The next real in-game discovery is still the exact amount: check 40/45/49/50 during one clean same-gender run. If count alone does not pass, test the character-copy / mirror relation before commands or mode routes.
