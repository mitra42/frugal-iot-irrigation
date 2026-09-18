# Plan 3 — leaving it running for days

This is the plan for someone who can put the board somewhere sunny, **switch charging on, and come
back to it over several days**. It is the only plan that tells us whether the thing works as a
solar charge controller rather than as a set of measurements.

## Is this the right plan for you?

Only if all of these are true:

- [Plan 1](plan-bench.md) is done.
- [Plan 2](plan-sunny-session.md) is done, **and someone has looked at your Part H numbers**. This
  matters: Part I lets the board decide its own charging, unattended, and if Part H showed our idea
  of the hardware is wrong then that is not something to leave running.
- The board can stay where it is, with sun on the panel, for **three days or more**, and you can
  look at it once or twice a day.
- The battery it is charging is one you know the type of — AGM, GEL, flooded, or LiFePO4.

If you are not sure what battery you have, **stop and ask**. Charging a battery to the wrong
voltage shortens its life, and in the worst case can make a sealed battery vent gas. This is the
one thing on any of these plans that can damage something.

## The order

| | Section | About | When |
|---|---|---|---|
| 1 | [Steps I1 and I1b](../TESTING.md#step-i1--set-the-battery-type) | tell it what battery, check the battery temperature sensor | 15 min |
| 2 | [Step I2](../TESTING.md#step-i2--switch-it-on) | set **Automatic** on | 1 min |
| 3 | [Step I3](../TESTING.md#step-i3--watch-what-it-says-it-is-doing) | watch what it says it is doing | first hour, then daily |
| 4 | [Step I4](../TESTING.md#step-i4--check-it-stops) | check it stops when the battery is full | day 1 or 2, afternoon |
| 5 | [Step I5](../TESTING.md#step-i5--the-usb-supply-if-your-board-has-one) | the USB supply, if your board has one | any time |
| 6 | [Step I7](../TESTING.md#step-i7--battery-charge-and-health-they-look-after-themselves) | charge and health readings | day 3 |
| 7 | [the sleep test](sleep-test.md) | what the outputs do while the board sleeps | last, needs a different build |

**Leave the sleep test until the end.** It needs software from a different branch, so you have to
flash the board again, and doing it earlier would interrupt the days of charging that are the
point of this plan.

## What to write down, and when

Once a day is enough, but please do it on paper or in a message at the time rather than from
memory afterwards:

- the time of day, and roughly what the weather was doing
- the **battery voltage** and the **Target** voltage the page shows
- which **stage** it says it is in
- the **panel voltage** and the **DAC step** number
- any temperature it shows

A week of once-a-day readings tells us more than an hour of watching it closely, because the
things that go wrong with a charge controller mostly go wrong overnight, or on the third cloudy day,
or when the battery reaches full for the first time.

## What we are watching for

- Does it ever ask for **more** charging than the panel can give, and sit there stuck?
- When the battery reaches full, does it **stop**, or does it keep pushing?
- Does the **Target** voltage move with temperature, as
  [Part I](../TESTING.md#part-i--letting-it-charge-by-itself) describes?
- Does it recover sensibly after a cloudy spell or overnight?
- Does the state-of-charge figure look anything like the truth?

## If something looks wrong

Set **Automatic** back to off. That stops the board charging on its own and puts it back where
[Plan 2](plan-sunny-session.md) left it — nothing is lost, and you can leave it there safely until
we have talked.

Tell us what it said at the time. The numbers on the page at the moment it looked wrong are worth
far more than a description afterwards.
