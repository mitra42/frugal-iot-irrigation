# Plan 1 — everything that does not need the sun

**This is the plan to start with**, whoever you are and whatever else you can do later. Nothing in
it depends on the weather, and none of it can harm the battery or the board.

## Is this the right plan for you?

Yes, if you have the board for **an afternoon or more**. It does not matter whether the sun is out,
and it does not matter whether the board is in its final position — a table indoors is fine.

If you also have sun and a multimeter, do [Plan 2](plan-sunny-session.md) afterwards. If you can
leave the board running for days, do [Plan 3](plan-long-run.md) after that.

## What you need

- The board, a USB data cable, a computer, and a phone or laptop with WiFi.
- A 12 V battery. **No solar panel needed** — if one is connected, disconnect it while you work.
- A multimeter, for one step only (see below if you have not got one).
- Whatever you have of: the soil probes, the valves, a tank float sensor, a bucket of water.

**Roughly 3 hours**, of which about half is waiting for things.

## The order

Work through [TESTING.md](../TESTING.md), in this order, skipping nothing in between:

| | Section | About | Needs |
|---|---|---|---|
| 1 | [Part A](../TESTING.md#part-a--getting-it-running) | getting the software on and talking to it | 30 min |
| 2 | [Part B](../TESTING.md#part-b--the-outputs-valves-pump-load) | the valve, pump and load outputs | 20 min, meter or one valve |
| 3 | [Part C](../TESTING.md#part-c--the-soil-probes) | the soil probes, added one at a time | 30 min, the probes |
| 4 | [Part D](../TESTING.md#part-d--the-water-tank-sensor) | the tank sensor | 30 min, the float sensor |
| 5 | [Part E](../TESTING.md#part-e--the-battery-reading) | is the battery voltage it reports correct | 10 min, **meter** |
| 6 | [Part F](../TESTING.md#part-f--a-complete-irrigation-run) | one whole watering run, start to finish | 30 min, water |
| 7 | [Part G](../TESTING.md#part-g--the-charge-controllers-own-measurements), steps **G2, G3 and G4 only** | which temperature sensor is which | 30 min |

**Skip step G1** — it needs the sun on the panel, and it belongs to [Plan 2](plan-sunny-session.md).

**Do not go on to Part H or Part I.** Both need sun, and Part I should not be switched on until
Part H's numbers have been looked at.

If you have not got some of the hardware — no probes, no tank sensor, no valves — skip that Part
and say so. The Parts do not depend on each other's equipment.

## If you have not got a multimeter

Do everything above except **Part E**, and tell us so.

It is worth knowing what this costs. Part E is what tells us whether the battery voltage the board
reports is the real one, and every protection in the software — when it stops watering, when it
sheds the load, when it decides the battery is full — is a decision made on that number. Without
Part E we cannot tell a correct reading from one that is out by a volt.

Parts G1 and H, in [Plan 2](plan-sunny-session.md), cannot be done at all without a meter, and
Part H is the single most useful measurement in the whole document.

Borrowing a meter for one afternoon is worth more to us than everything else on this list put
together. Almost any meter will do; it only has to read DC volts up to about 30 V.

## When you have finished

Send back what [How to report what you find](../TESTING.md#how-to-report-what-you-find) asks for —
step numbers, the actual numbers you measured, and photographs of anything that did not look like
the description.

Also send your answers to [HARDWARE-QUESTIONS.md](../HARDWARE-QUESTIONS.md) if you have not already.
Several of them are questions the steps above will have put in front of you anyway.
