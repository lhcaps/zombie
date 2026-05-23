# Zombie Almighty Quest - Current SOT

Date: 2026-05-21

This file keeps only the current usable theory after the latest hard correction:

```text
zombifying another Quincy or being zombified is not needed
```

That correction removes the old chain theory where B had to be another Zombie/Quincy user or where the quest holder had to become a zombie.

## Latest Read

The quest is best treated as a constraint satisfaction problem.

Oasis compared the drawing to constraint satisfaction equations and gave "no comment" to Sudoku. Cristi also said the quest assigns a path: same quest, same assignment, different order / starting point.

The latest green-only image has eight readable marks if the center and small mark are counted. The cleanest use of that is not a physical formation, but the eight possible M/F assignments for three binary variables.

## Current Model

```text
A = quest holder starting gender
B = first target gender
C = second target gender

Domain = M or F
Path = A_start + B_target + C_target
Possible paths = MMM, MMF, MFM, MFF, FFF, FFM, FMF, FMM
```

The phrase "You do it twice" is most cleanly satisfied by two manual zombifications:

```text
A zombifies B
A gender swaps
A zombifies C
```

The zombies do not need to act.

## Why This Satisfies The Hints

| Hint | Fit |
|---|---|
| Can be done in any world | No map dependency. |
| Can be done in base | No Volt/mode required. |
| Zombification required | B and C must become zombies. |
| Zombies do not need to do anything | B/C are passive after conversion. |
| Need players, but not player requirement | B/C are variables/targets, not special quest holders. |
| No specific elements | Only Zombie passive/manual grip is used. |
| Gender swap required | A swaps between the two zombifications. |
| Niche / stupid requirement | Gender path plus passive Blood Bar is specific but easy once known. |
| Giselle would do it | Turn people into zombies and control them without them acting. |
| Manual gripping required | Both conversions use manual grip. |
| No alts/friends needed | Can be done with available players, no dedicated alternate required. |
| Another Quincy not needed | B/C can be any race. |
| Do not need to zombify yourself | A never becomes zombie. |
| Blood Bar passive | B/C bars are built through passive. |
| You do it twice | Two zombifications. |
| TF2 autobalance | Male/Female balancing and assigned path/order. |
| You won't know what you did | The final check only happens after both hidden constraints are satisfied. |
| Become like them...then control their minds | Become like Giselle's method: create zombies, not become a zombie yourself. |

## Clean Test Route

For one path, example `FMF`:

1. Set A to Female.
2. Set B to Male.
3. A lets B hit them with M1s to build B Blood Bar through Zombie passive.
4. A knocks B.
5. A manually grips B.
6. Confirm B becomes zombie.
7. B does nothing.
8. A gender swaps.
9. Set C to Female.
10. A lets C hit them with M1s to build C Blood Bar through Zombie passive.
11. A knocks C.
12. A manually grips C.
13. Confirm C becomes zombie.
14. C does nothing.
15. Check Jugram/Balance only now.

## Path Set

```text
MMM
MMF
MFM
MFF
FFF
FFM
FMF
FMM
```

Do not mix extra variables into the first pass. Run one path cleanly, log it, then move to the next path.

## Deprioritized Theories

- A must become zombie: contradicted by latest correction.
- B must be another Zombie user: contradicted by latest correction.
- B must zombify C: makes zombies do work, weaker against latest hints.
- Another Quincy required: explicitly not needed.
- Volt/Implode route: conflicts with base/no-mode hints.
- Hidden command route: conflicts with zombies not needing to do anything.
- Physical 8-player grid: the CSP/Sudoku hint makes the eight marks more likely to mean eight binary assignments.

## Current Best Answer

Complete the assigned A/B/C gender path:

```text
A passive-fills B -> A manual-grips B -> B becomes zombie
A gender swaps
A passive-fills C -> A manual-grips C -> C becomes zombie
Check Jugram/Balance
```

If it fails, test the other A/B/C paths before returning to older matrix/count theories.
