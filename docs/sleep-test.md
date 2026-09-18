# The sleep test — what the outputs do while the board is asleep

This one needs a **different build of the software**, and a multimeter. It is the last thing on
[Plan 3](plan-long-run.md), and it decides whether we can use a power-saving feature at all.

## Why

The board can be told to sleep when the battery is low, so that the solar panel gets a chance to
recharge it. But while an ESP32 sleeps, its output pins are normally *released* — they stop being
driven — and we do not know what this board does then.

The original software sets pin 14 with a "pull-up". If that still applies while the board is
asleep, it would switch the load **on** at exactly the moment we were trying to save power. And if
sleeping stops the charging, the battery cannot recover during the very sleep meant to let it.

Either way round, sleeping would make things worse rather than better, and we would leave the
feature switched off. It is off today for exactly this reason.

## The test build

There is a branch called `sleep-test`. It is the ordinary software with one thing changed: instead
of staying awake all the time, it **sleeps on a repeating cycle — 5 minutes awake, then 2 minutes
asleep, over and over**.

Nothing triggers it and nothing has to be timed. You wait for the next sleep, take your reading,
and if you miss it the window comes round again seven minutes later.

To build and flash it:

```bash
git checkout sleep-test
git pull
pio run --target upload --environment ff_openmppt
```

If you did not build the software yourself for
[Step A1](../TESTING.md#step-a1--put-the-software-on-the-board) but were sent a file to flash, you
will need a file for this too — ask, the same way.

### Knowing when it is asleep

- The board's page **stops responding**, and comes back about two minutes later.
- If the USB cable is plugged into a computer with a serial monitor open, this build prints
  `Sleeping` just before it goes.
- Waking is a full restart, so it reconnects to WiFi each time. Give it twenty seconds or so before
  expecting the page back.

That restart is also why irrigation goes back to idle after each sleep. That is normal and is not
what we are testing here.

## Which output to measure

**Pin 14**, which the board's page calls **Pump**. Use the same terminal you measured in
[Step B2](../TESTING.md#step-b2--switch-each-output-on-and-off), with the meter set up the same
way: black probe on the battery's negative terminal, red probe on the output.

The page calls it Pump because that is the role this software gives pin 14. The original OSPIT
software uses the same pin as its **load** switch — the one that would have the router on it — and
that is why this particular pin is the one worth measuring. It is the same pin and the same
circuit either way.

## The measurements

Six readings. Take them at the board's terminals with the meter, not from the page — the whole
question is what the hardware does when the software is not running.

**Pin 14 / Pump**

1. During an awake period, switch **Pump** on. Measure the voltage at its terminal. Write it down.
2. Wait for it to go to sleep. Measure the **same terminal again while it is asleep**. Does it stay
   on, or go off?
3. During the next awake period, switch **Pump** off. Measure the terminal.
4. Wait for the next sleep and measure again. Does it stay off, or come on?

Reading 4 is the one we are most worried about.

**The solar charging**

5. While it is awake and charging normally, note the **solar panel voltage** at the panel
   terminals.
6. Wait for it to sleep, and measure the panel voltage again while asleep. Does charging carry on,
   stop, or change?

Do 5 and 6 in reasonably steady sunshine if you can — a cloud crossing between the two readings
will change the voltage by itself and tell us nothing.

**While you are there**, if you have a spare moment during any sleep, put the probe on **Valve 1**
with the valve switched off and tell us what you see. A valve that comes on while the board is
asleep matters a good deal more than a router does, and it is the same measurement.

## Putting it back

```bash
git checkout main
pio run --target upload --environment ff_openmppt
```

The board then stays awake all the time again, as it does for every other test. Nothing you set on
the page is lost — settings live on the board and survive both the sleeping and the reflashing.

## What to send back

The six numbers, and for each of 2, 4 and 6, which of the outcomes it was. If the output behaved
differently on different sleeps, say so — an output that is inconsistent is a more interesting
answer than either of the tidy ones.
