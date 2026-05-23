# Zombie Almighty Workspace

This folder is organized around the latest usable Zombie Almighty theory and test material.

## Use These First

Final shareable files are in `00_FINAL/`:

- `Zombie Almighty.docx`
- `Zombie Almighty.pdf`

Use this package when sharing the current final:

```text
Zombie Almighty.zip
```

Newest working note after the SideCharacter update:

```text
02_WORKING_NOTES/ZOMBIE_QUEST_SIDECHARACTER_UPDATE.md
```

Current best theory:

```text
Gender reroll exactly once
-> zombify about 50 same-gender targets through passive Blood Bar + manual grip
-> resolve two hidden tail checks:
   copy/mirror character appearance
   plus same-gender final zombify/check while that relation is active
```

Latest simulation command:

```text
cd 03_TOOLS
python zombie_test_runner.py --mode=simulate
```

Latest simulator result points to `char + mirror + gender`, not items/accessories, commands, Volt/mode, or repeated gender rerolls.

Deprecated previous CSP theory, kept only for reference:

```text
A = quest holder starting gender
B = first target gender
C = second target gender

Path = A/B/C gender assignment
Domain = M or F
Possible paths = MMM, MMF, MFM, MFF, FFF, FFM, FMF, FMM
```

Clean test route:

```text
one gender reroll
-> same-gender passive Blood Bar
-> knock
-> manual grip
-> confirm zombie
-> repeat/check at 40, 45, 49, 50
-> if no pass, test copy/mirror character appearance plus same-gender final grip while active
```

Important hard constraints:

- No Volt/mode for clean tests.
- No commands (`return`, `die`, `invade`).
- Zombies do not need to do anything.
- Quest holder does not need to be zombified.
- Zombifying another Quincy is not needed.
- Use passive Blood Bar and manual grip.
- Do not use old repeated-reroll A/B/C or 2x2 matrix routes as the main path.

## Folder Map

- `00_FINAL/` - latest usable `Zombie_Almighty` final artifacts.
- `01_SOURCES/` - original docs, hint images, Cristi screenshots, and extracted source text.
- `02_WORKING_NOTES/` - current markdown notes and latest green-only image analysis.
- `03_TOOLS/` - current final builder and latest test/scoring tools.
- `03_TOOLS/build_zombie_almighty.py` - generates `Zombie Almighty.docx` and `Zombie Almighty.pdf`.
- `03_TOOLS/zombie_tail_simulator.py` - current scorer for the last two-ish tasks.
- `99_ARCHIVE_OLD_RUNS/2026-05-21_cleanup/` - old scripts, old analyses, old reports, old generated outputs.

## Deprecated Files

The older final docs with `Type_Soul_*`, `CSP`, `Deduction_Matrix`, and old reassessment names predate the SideCharacter update. They were moved to:

```text
99_ARCHIVE_OLD_RUNS/2026-05-22_zombie_almighty_replaced_outputs/
```

The old root `zombie.zip` was moved there as well. Use `Zombie Almighty.zip`.

## Note

`_Zombie Checklist Database.docx` is also still visible in the root because it was locked by another process during cleanup. A complete copy is already preserved at:

```text
01_SOURCES/_Zombie Checklist Database.docx
```

Once the lock is gone, the root duplicate can be moved or removed.
