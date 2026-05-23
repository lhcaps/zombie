# Zombie Quest — New Hint Reassessment

**Date:** 2026-05-21

---

## What the New Hint Means

> "Constraint Satisfaction, but in a functional way. You do not need to know computer science to solve it."

This is a small **input/output puzzle**. Think of it as a function: you give it specific inputs (genders), it produces a result (zombification). Do not overthink it as a programming problem or a physical formation.

---

## The Core Model

The quest is a function with **two inputs**:

```
f(actor_gender, target_gender) = passive Blood Bar → knock → manual grip → target becomes zombie
```

Every zombification follows this exact sequence. Nothing else is required of the target.

### Variables

| Variable | Meaning |
|---|---|
| **Actor** | The player doing the quest |
| **Target** | The player being zombified |

### Domain

Each variable takes one of two values: **M** (Male) or **F** (Female).

### Gender Pairs

There are four possible actor/target combinations:

| Pair | Actor | Target |
|---|---|---|
| **MM** | Male | Male |
| **FF** | Female | Female |
| **MF** | Male | Female |
| **FM** | Female | Male |

Each pair must be completed **twice** (`x2`). This gives eight total zombifications.

### The Function Sequence (for every pair)

```
1. Target builds Blood Bar through Zombie passive
2. Actor knocks the target
3. Actor manually grips the target
4. Target becomes a zombie
5. Zombie does nothing — no commands, no actions
```

---

## Why This Fits the Hints

| Hint | How It Matches |
|---|---|
| "You do it twice" | Each gender pair is done x2 |
| "TF2 autobalance us" | Same-gender (MM, FF) and opposite-gender (MF, FM) pairs both covered |
| "Constraint Satisfaction" | Function with inputs from a finite domain |
| "Functional" | Input → fixed process → output |
| "Gender swap required" | Actor swaps gender between blocks |
| "Blood Bar passive involved" | Passive is the first step of every zombification |
| "Manually gripping required" | Manual grip is the final step of every zombification |
| "Zombies do not need to act" | Target becomes zombie and does nothing |
| "Can be done in base" | No Volt/mode needed |
| "Any race, any world" | No element or map restrictions |

---

## What the Image Really Shows

The green marks in the image represent the **four gender pairs**, not an 8-player physical formation. Purple and red elements are annotations — ignore them unless a future hint gives them meaning.

---

## How to Run It

### If You Start as Male

```
1. Start as Male
2. MM x2  (zombify 2 male targets)
3. Swap to Female
4. FF x2  (zombify 2 female targets)
5. Swap to Male
6. MF x2  (zombify 2 female targets)
7. Swap to Female
8. FM x2  (zombify 2 male targets)
9. Check NPC (Jugram/Balance)
10. Optional: swap back to Male and check again
```

### If You Start as Female

```
1. Start as Female
2. FF x2  (zombify 2 female targets)
3. Swap to Male
4. MM x2  (zombify 2 male targets)
5. Swap to Female
6. FM x2  (zombify 2 male targets)
7. Swap to Male
8. MF x2  (zombify 2 female targets)
9. Check NPC (Jugram/Balance)
10. Optional: swap back to Female and check again
```

---

## If the Main Route Fails

**Step 1:** Swap back to your starting gender and check the NPC again.

**Step 2:** Try a **rotation** — change the order of the four blocks but keep the method and count exactly the same. There are four possible rotations:

```
MM → FF → MF → FM
FF → MF → FM → MM
MF → FM → MM → FF
FM → MM → FF → MF
```

**Step 3:** Only after the above fail, treat the A/B/C gender-path model (8 independent paths: MMM, MMF, MFM, MFF, FFF, FFM, FMF, FMM) as a fallback.

---

## Hard Rules — Do Not Break

For a clean test, the following are **not allowed**:

```
- return, die, invade commands
- Volt or mode
- Zombie actions after conversion
- Quincy-only or specific-race targets
- Self-zombification
- Cosmetics, name, or accessory requirements
- Any "extra" mechanic not in the function sequence above
```

The only mechanics that matter: **passive Blood Bar → knock → manual grip**. Everything else is noise.

---

## What to Log Per Run

```
Run ID:
Starting gender:
Path tested:
Pair-by-pair log (MM/FF/MF/FM x2):
  - each target gender and race
  - passive fill confirmed
  - knock confirmed
  - manual grip confirmed
  - zombie confirmed
  - zombie action: none
Gender swaps confirmed:
Commands used: none
Volt/mode used: none
NPC result:
Pass / Fail:
Notes:
```
