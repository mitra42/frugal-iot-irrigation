# Plan 2 — one sunny half-day

**This is the most valuable half-day you can give us.** It is the only plan that measures what the
solar charge hardware actually does, and that is the one thing we cannot work out from here.

## Is this the right plan for you?

Yes, if you have **sun on the panel**, a **multimeter**, and about **an hour and a half**.

Do [Plan 1](plan-bench.md) first if you can. If you cannot — if this is your only session with the
board — then do Part A out of it first, so the board is running and you can see its page, and skip
the rest.

**Morning is much better than afternoon.** The test needs a battery that is *not already full*: a
full battery will not take charge however hard we ask it to, and the measurements will all come
out the same and tell us nothing.

## What you need

- The board running, with its page open on a phone or laptop — [Part A](../TESTING.md#part-a--getting-it-running).
- The solar panel connected, in the sun, with as little moving cloud as you can manage.
- The 12 V battery, **not fully charged**.
- A multimeter.

**Safety.** Disconnect the solar panel before you connect or disconnect anything else. A panel in
sunlight is live even when nothing is switched on, and you cannot turn it off — only cover it or
unplug it. And do not disconnect the battery while the panel is connected: the battery is what
absorbs the panel's power, and without it the charge circuit has nowhere to put it.

## The order

| | Section | About | Needs |
|---|---|---|---|
| 1 | [Step G1](../TESTING.md#step-g1--the-solar-panel-voltage) | is the panel voltage it reports correct | 15 min |
| 2 | [Part H](../TESTING.md#part-h--setting-the-charger-by-hand) | working the charger by hand, 0 to 255 | 45 min |

That is all. Two things, and the second one is the point of the exercise.

**Part H cannot harm the battery.** Every setting it asks you to try draws the same charging
current as now, or less. Nothing in it can overcharge anything. If at any moment you are
uncomfortable, set the number back to **255**, which is the gentlest setting, and stop.

**Do not go on to Part I** in this session. Part I lets the board charge on its own, unattended,
and it should not be switched on until someone has looked at your Part H numbers. It is
[Plan 3](plan-long-run.md).

## What we are actually asking

Our software sets charging by sending the hardware a number from 0 to 255. We believe 0 asks for
the most charging and 255 for the least — backwards from what anyone would expect — but we have
never been able to check it, because we have never had the board.

So the numbers you write down in [Step H2](../TESTING.md#step-h2--work-through-the-settings) are
not a formality. They are how we find out whether our idea of this hardware is right at all. A
table of eight readings from you settles a question we have otherwise had to guess at.

**Please write down the actual numbers**, including any that look wrong to you. A reading that
looks wrong is more useful than one that looks right, because it usually points straight at which
part of the software is mistaken.

## When you have finished

Send back what [How to report what you find](../TESTING.md#how-to-report-what-you-find) asks for.
For this plan especially, send the whole table from Step H2 even if you did not finish it.
