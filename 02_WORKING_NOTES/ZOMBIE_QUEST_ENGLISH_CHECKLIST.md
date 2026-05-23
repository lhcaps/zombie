# Type Soul Almighty Zombie Quest Checklist

Use this as the current clean manual test checklist for the Zombie Almighty step.

## Golden Rule

- [ ] Do not check Jugram/Balance after each small step.
- [ ] Check Jugram/Balance only after the full candidate route is complete.
- [ ] A pass should show the next Almighty step / "NEXT GIFT IN ORDER".
- [ ] If the route fails, log it as a failed candidate and move to the next path.

## Latest Hard Corrections

- [ ] Zombifying another Quincy is not needed.
- [ ] Being zombified yourself is not needed.
- [ ] Another Zombie user is not needed.
- [ ] Zombies do not need to do anything after they become zombies.
- [ ] Do not use zombie commands for the clean test.

## Hard Constraints

- [ ] A is on the Zombie part of the Almighty questline.
- [ ] A is using Zombie schrift.
- [ ] The route can be done in base.
- [ ] No Volt/mode for clean tests.
- [ ] No return, die, invade, or hidden zombie command.
- [ ] No specific world, clan room, race, element, accessory, outfit, or name.
- [ ] Every zombification must be through manual grip.
- [ ] The target must actually become a zombie.
- [ ] Blood Bar should be built through the Zombie passive whenever possible.
- [ ] B and C can be any race unless a fallback test says otherwise.

## CSP / Sudoku Model

Oasis compared the hint image to constraint satisfaction equations and gave "no comment" to Sudoku.

Treat the quest like variables under constraints:

```text
A = quest holder starting gender
B = first target gender
C = second target gender

Domain = M or F
Path = A_start + B_target + C_target
```

The eight possible paths are:

```text
MMM, MMF, MFM, MFF, FFF, FFM, FMF, FMM
```

## Clean Route For One Path

Example path: `FMF`.

- [ ] Set A to Female before starting.
- [ ] Set B to Male.
- [ ] A lets B hit them with M1s to build B's Blood Bar through Zombie passive.
- [ ] A knocks B.
- [ ] A manually grips B.
- [ ] Confirm B becomes zombie.
- [ ] Do not command B. B does nothing.
- [ ] A gender swaps.
- [ ] Set C to Female.
- [ ] A lets C hit them with M1s to build C's Blood Bar through Zombie passive.
- [ ] A knocks C.
- [ ] A manually grips C.
- [ ] Confirm C becomes zombie.
- [ ] Do not command C. C does nothing.
- [ ] Check Jugram/Balance only now.

## Path List

If A starts Male:

- [ ] `MMM`
- [ ] `MMF`
- [ ] `MFM`
- [ ] `MFF`

If A starts Female:

- [ ] `FFF`
- [ ] `FFM`
- [ ] `FMF`
- [ ] `FMM`

For every path:

- [ ] Keep A as the quest holder.
- [ ] Keep B as the first target.
- [ ] Keep C as the second target.
- [ ] Use passive Blood Bar for B and C.
- [ ] Use manual grip for B and C.
- [ ] Do not let zombies perform an action.
- [ ] Check Jugram/Balance only after both zombifications.

## Fallback Order

Only change one variable at a time.

- [ ] Run all eight A/B/C paths with the same clean method.
- [ ] Repeat the same path with B and C at 100% Blood Bar.
- [ ] Repeat the same path with B and C below 100% Blood Bar.
- [ ] Repeat the same path with fresh targets only.
- [ ] Repeat the same path reusing the same target only if practical.
- [ ] Test race variants only after gender paths fail.

## Old 2x2 Matrix Fallback

Use only after the clean CSP route fails.

```text
MM x2 -> swap -> FF x2 -> swap -> MF x2 -> swap -> FM x2 -> swap back -> check NPC
```

Female-start mirror:

```text
FF x2 -> swap -> MM x2 -> swap -> FM x2 -> swap -> MF x2 -> swap back -> check NPC
```

## What Not To Add

- [ ] No return.
- [ ] No die.
- [ ] No invade.
- [ ] No hidden command.
- [ ] No Volt.
- [ ] No Implode.
- [ ] No T/G/Z/X/C as the main Blood Bar source.
- [ ] No Quincy-only requirement.
- [ ] No self-zombify requirement.
- [ ] No zombie action requirement.
- [ ] No 8-player physical grid/formation.

## Run Log

```text
Run ID:
Date:
Server/world:
Path tested:
A start gender:
B target gender/race:
C target gender/race:
B Blood Bar method/value:
B manual grip confirmed:
B became zombie:
A gender swap confirmed:
C Blood Bar method/value:
C manual grip confirmed:
C became zombie:
Commands used: No
Volt/mode used: No
Final Jugram/Balance result:
Pass/fail:
Notes:
```

## Current Best Run To Try First

```text
Pick one A/B/C path.
A passive-fills B -> A manual-grips B -> B becomes zombie.
A gender swaps.
A passive-fills C -> A manual-grips C -> C becomes zombie.
Check Jugram/Balance only after both zombifications.
```
