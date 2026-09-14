# Testing on real hardware

This guide is for the person who has the board in their hands. You do **not** need to understand
the software. Each step tells you what to do, what you should see, and what it means if you see
something else.

Please work through the steps **in order**. Each one depends on the ones before it. If a step
fails, stop there and report it — going on will only produce confusing results.

## Before you start

**You need:**

- The board, and a USB cable that carries data (some charging cables carry power only — if the
  computer does not notice the board when you plug it in, try another cable).
- A multimeter.
- A phone or laptop with WiFi.
- A 12 V battery. A solar panel if you have one.
- The soil probes, valves, and the tank float sensor if you have them.

**You do not need** a laboratory power supply. Nothing here asks for one.

**Safety.** Disconnect the solar panel before you connect or disconnect anything else. A panel in
sunlight is live even when nothing is switched on, and you cannot turn it off — you can only cover
it or unplug it.

## How to report what you find

For each step, please send back:

- the **step number**
- what you saw
- any numbers you measured — please write down the **actual numbers**, not "about right"
- a photograph if anything looks physically different from what the step describes

Numbers that look wrong are much more useful to us than a description, because the wrong number
often tells us exactly which part of the software is mistaken.

---

# Part A — Getting it running

## Step A1 — Put the software on the board

If you build it yourself, see [README.md](README.md). Otherwise we will send you a file to flash.

**You should see:** the board's small light blinks, or the screen lights up, within a few seconds
of power being applied.

**If nothing happens:** check the USB cable first (see above), then tell us — do not continue.

## Step A2 — Connect to the board's own WiFi

The board makes its own WiFi network when it does not know any other one.

1. On your phone, look at the list of WiFi networks. One of them starts with `frugal-iot`.
2. Connect to it. There is no password.
3. A page should open by itself. If it does not, open a browser and type: `192.168.4.1`

**You should see:** a page listing the things the board can measure and control.

**If the page does not appear:** some phones quietly switch back to mobile data when a WiFi
network has no internet. Look for a message like "This network has no internet — stay connected?"
and choose to stay.

## Step A3 — Set the clock

Irrigation happens at a time of day, so the board has to know the time.

1. On that same page, find the line showing the date and time.
2. If it is wrong, or the year says 1970, press the **Set time** button. This copies the time from
   the phone you are holding.

**You should see:** the correct local date and time.

## Step A4 — Give it your WiFi (optional at this stage)

If there is WiFi where the board is, enter its name and password on the same page. The board will
then also appear on the dashboard and you can watch it from anywhere. Everything below works
without this.

---

# Part B — The outputs (valves, pump, load)

In this part you check that each output switches, and that the right output switches.

**Do this with the valves disconnected the first time.** You are testing the board, and a valve
that turns out to be wired to the wrong output is easier to find without water involved.

## Step B1 — Find the output terminals

Set your multimeter to measure **DC volts**. Put the black probe on the negative/ground terminal
of the battery, and the red probe on the output terminal you are testing.

## Step B2 — Switch each output on and off

On the board's page, find the section for each valve in turn: **Valve 1**, **Valve 2**,
**Valve 3**, and **Pump** if your board has one.

For each one:

1. Switch it **on**. Measure the voltage at its terminal. Write it down.
2. Switch it **off**. Measure again. Write it down.

**You should see:** roughly battery voltage (around 12 V) when on, and close to 0 V when off.

**Please record a table like this:**

| Output | Voltage when ON | Voltage when OFF |
|---|---|---|
| Valve 1 | | |
| Valve 2 | | |
| Valve 3 | | |
| Pump | | |

**Things that would be important to tell us:**

- Switching **Valve 1** on the page makes a **different** terminal turn on. That means the pin
  numbers in our software are wrong, and we need to know which one actually moved.
- An output is already on before you touch anything.
- An output never reaches battery voltage but sits at some middle value.

## Step B3 — Now connect one valve

Connect a single valve to output 1 and repeat step B2 for it. You should hear or feel it click.

**If the valve does not move but the voltage was correct in B2:** the valve needs more current
than the board can supply directly, and needs a relay between them. Tell us what the valve is.

---

# Part C — The soil probes

The probes talk to the board over a pair of wires shared by all of them. Each probe needs its own
**address** so the board can tell them apart. **Probes arrive from the factory all using the same
address (1).** If you connect two new probes at once, they both answer at the same time and the
board understands neither.

So the probes must be connected **one at a time**, in order.

## Step C1 — Connect the first probe only

Connect **one** probe to the RS485 terminals (often marked A and B, or D+ and D−). Leave the
others unconnected.

Wait about two minutes.

**You should see:** on the board's page, **Sector 1 probe** starts showing a moisture percentage
and a temperature.

**If nothing appears:** try swapping the two wires (A and B). Getting them the wrong way round is
very common and does no damage.

## Step C2 — Add the second probe

**Without disconnecting the first**, connect the second probe. Wait about two minutes.

**You should see:** **Sector 2 probe** starts showing readings too, and Sector 1 keeps working.

What happened: the board noticed a new probe using the factory address, and gave it the address
for sector 2 automatically.

## Step C3 — Add the third probe

Same again. Wait two minutes. **Sector 3 probe** should appear.

## Step C4 — Check they are the right way round

Hold **one** probe in your hand, or put it in a glass of water, and watch which sector's number
changes.

**Please record:** which physical probe corresponds to Sector 1, Sector 2 and Sector 3. Mark the
probes with tape so you do not lose track.

**If two probes ever show exactly the same number at exactly the same time,** they have ended up
sharing an address. Tell us — do not try to fix it yourself.

---

# Part D — The water tank sensor

Skip this part if no tank sensor is fitted.

The tank sensor is a float that moves up and down inside the tank. The board has to be told what
"empty" and "full" look like, because every tank is different.

## Step D1 — With the tank empty

1. Make sure the float is at the bottom (tank empty), or hold it at the bottom by hand.
2. On the board's page, find the **Water tank** section.
3. Press the button marked **Tare**. ("Tare" means "call this reading zero".)

**You should see:** the tank reading becomes 0%.

## Step D2 — With the tank full

1. Fill the tank, or hold the float at the top.
2. In the **Water tank** section, find the box next to **Calibrate**. Type `100` and send it.

**You should see:** the tank reading becomes 100%.

## Step D3 — Check it in between

Let the float sit at roughly half height.

**You should see:** somewhere near 50%. It does not need to be exact.

**Please record:** the readings at empty, half and full.

**If the reading goes DOWN as the tank fills up,** tell us — the sensor is wired the opposite way
to what we assumed, and it is a one-line change.

---

# Part E — The battery reading

The board measures the battery through two resistors. We need to know whether our arithmetic
matches your board.

**You cannot do this in one sitting** — you need the battery at different voltages, and the only
way to get that without special equipment is to wait. Three measurements over two days is enough.

## Step E1 — Measure and compare

Each time:

1. Measure the **actual** battery voltage with your multimeter, directly at the battery terminals.
2. Read the **Battery** value on the board's page. It is shown in millivolts, so 12.45 V appears
   as about `12450`.
3. Write both down, with the time.

**Please do this three times:**

| When | Meter reading (V) | Board reading (mV) |
|---|---|---|
| After dark, battery resting | | |
| Early morning, before the sun reaches the panel | | |
| Middle of a sunny day, while charging | | |

**What we are looking for:** whether the board's number is consistently a fixed percentage away
from the meter. If it is, that is one number for us to correct and it is easy. If the error
changes size at different voltages, that is more interesting and we need all three readings to
see it.

---

# Part F — A complete irrigation run

Now put it together. **Do this where spilled water does not matter**, or with the valves
connected to nothing.

## Step F1 — Set a start time two minutes from now

1. Look at the clock. Add two minutes. For example, if it is 14:37 now, your target is 14:39.
2. On the board's page, find the **Irrigation** section.
3. In **Start hour**, type the hour — `14` in this example. Send it.
4. In **Start minute**, type the minute — `39`. Send it.

## Step F2 — Set a short watering time

In the same section, find **Max minutes per sector** and set it to `1`. This is the longest any
one valve stays open. One minute keeps the test short.

## Step F3 — Make sure a sector actually wants water

A sector is only watered if its soil is drier than its target. Look at each sector's **Target**
and at the matching probe's moisture reading.

To force sector 1 to water: set its **Target** to a number **higher** than what the probe reads
now. If the probe reads 30, set the target to 90.

## Step F4 — Turn irrigation on

Find **Enabled** in the **Irrigation** section and switch it on.

## Step F5 — Watch

**You should see, at your target time:**

1. Valve 1 opens. **Active sector** shows `1`.
2. After at most one minute, valve 1 closes and valve 2 opens (or is skipped if sector 2 does not
   want water).
3. When all sectors are done, **Active sector** goes back to `0` and every valve is closed.

**Please record:** the time each valve opened and closed.

**If nothing happens at the target time:** check the clock again (step A3). This is the most
common cause by far.

## Step F6 — Check a sector with no probe is left alone

1. Disconnect the probe for sector 3.
2. Run the test again (steps F1 and F4 — you will need to set the time again).

**You should see:** sectors 1 and 2 behave as before, and valve 3 **never opens**. This is
deliberate: the board will not open a valve it has no measurement for.

---

# Part G — The charge controller's own measurements

The board can measure its solar panel and its own temperature. **None of this controls anything** —
the software only reads and reports. Controlling the charging comes later, and it will not be added
until these readings have been checked against your meter, because a charger working from a wrong
reading can damage a battery.

## Step G1 — The solar panel voltage

**Safety first.** A solar panel in daylight is live and cannot be switched off. Do not touch the
bare metal of the panel terminals. Measure at the board's terminals, with the panel connected.

1. Set your multimeter to **DC volts**.
2. Measure across the board's **solar panel** input terminals.
3. Read **Solar Panel** on the board's page. It is in millivolts, so 18.4 V appears as about
   `18400`.

Do this **three times on the same day**:

| When | Meter (V) | Board (mV) |
|---|---|---|
| Early morning, sun just reaching the panel | | |
| Middle of the day, full sun | | |
| Panel covered with a cloth or cardboard | | |

**What we are looking for:** whether the board's number tracks the meter, and whether the
difference stays the same size or grows as the voltage rises.

**If the board reads roughly zero all day** while your meter shows a real voltage, the panel is
probably connected to a different terminal than we assumed. Photograph the connections.

## Step G2 — Which temperature sensor is which

The board can have up to three temperature sensors on one shared pair of wires. They all look the
same to the software, so it has to be told which is which — **once**, and it remembers.

1. On the board's page you should see **Air Temperature**, **Battery Temperature** and
   **Board Temperature**. Some may show `--`, meaning nothing is assigned to them yet.
2. If more than one sensor is connected, each of those three has a **drop-down list** of the
   sensors found, showing long codes like `28a1b2c3d4e5f601`. That code is printed into the
   sensor at the factory and never changes.

### The easy way: connect them one at a time

If you can unplug the sensors, this is much easier than guessing, because at each step the code
that has just **appeared** is certainly the sensor you have just plugged in.

1. Disconnect all three sensors.
2. Connect **one**. Wait about a minute.
3. One code now appears in the drop-down lists. Choose it under the name that matches where that
   sensor is physically attached — for example, the one clipped to the battery goes under
   **Battery Temperature**. The choice is remembered, and survives switching the board off.
4. Connect the **second** sensor. Wait a minute. A second code appears. Assign it the same way.
5. Connect the **third**. You do not have to do anything: with only one name left unassigned and
   only one sensor unclaimed, the board matches them up by itself.

Write down each code and where that sensor is, so you have a record.

### The other way: if they are already all connected

If unplugging them is difficult, you can find each one by warming it:

1. Hold **one** sensor in your closed hand for a minute, or warm it gently. Do not use a flame.
2. Watch the three temperature readings. The one that rises is the sensor you are holding.
3. In the drop-down for the **correct name**, choose the code that just moved.
4. Repeat for each sensor.

**Please record:** each code and where that sensor is physically attached.

**If there is only one sensor connected in total,** it is assigned automatically and there is
nothing to do.

## Step G3 — Sanity-check the temperatures

With everything at room temperature and the board not working hard, all the sensors should read
within a degree or two of each other, and within a degree or two of the room.

**Please record:** the three readings, and the actual room temperature if you can measure it.

**If one reads about −127,** that sensor is not answering — check its wiring.

## Step G4 — The heatsink (only if question 4 applies)

If your board has the **pair of small diodes** near the heatsink rather than a temperature sensor
(see question 4 in [HARDWARE-QUESTIONS.md](HARDWARE-QUESTIONS.md)), tell us — we will send you a
build with that reading switched on. It is written but turned off by default, because we believe
most boards use the other method and having both would give two different answers to the same
question.

---

# Part H — Setting the charger by hand

**This is the most valuable measurement in this document.** It tells us how the number our
software sets relates to what the hardware actually does, which is the one thing we cannot work
out without your board.

The board controls charging by telling the solar charge circuit what voltage to hold the solar
panel at. Our software sets that as a number from **0 to 255**. We believe — but have not been
able to check — that:

- **0** asks for the lowest panel voltage, which draws the **most** charging current
- **255** asks for the highest panel voltage, which draws the **least**

So the number works backwards from what most people expect, and confirming that is part of the
point of this test.

## Before you start

**Conditions you need:**

- A **sunny day**, with the sun on the panel, and ideally not much cloud moving across.
- A battery that is **not already full** — early in the day is best. A full battery will not accept
  charge whatever we ask for, and the test will show nothing.
- About 30 minutes.

**Safety.** Do not disconnect the battery while the solar panel is connected. The battery is what
absorbs the panel's power; without it the charge circuit has nowhere to put it.

**This test cannot harm the battery.** Every setting asks for *less* charging than the panel could
give, or the same. Nothing here can overcharge anything. If you are worried at any point, set the
number back to **255**, which is the gentlest setting.

## Step H1 — Find the control

On the board's page, find the section called **Charge Control**. It has:

- **DAC step** — the box you type in, 0 to 255
- **Panel target** — what the software *predicts* the panel voltage will be. **This is a guess.**
  Checking it against your meter is exactly what this test does.
- **DAC volts** — an internal value; ignore it.

It starts at 255.

## Step H2 — Work through the settings

For each number in the table below:

1. Type it into **DAC step** and send it.
2. **Wait 30 seconds** for things to settle.
3. Measure the **solar panel** voltage with your meter, at the board's panel terminals.
4. Measure the **battery** voltage with your meter, at the battery terminals.
5. Write down both, and what the page shows under **Panel target**.

| DAC step | Panel target says (V) | Panel measured (V) | Battery measured (V) |
|---|---|---|---|
| 255 | | | |
| 230 | | | |
| 200 | | | |
| 170 | | | |
| 140 | | | |
| 110 | | | |
| 80 | | | |
| 50 | | | |
| 25 | | | |
| 0 | | | |

Please also note **roughly what the weather was doing** — full sun, thin cloud, and whether it
changed while you worked through the table.

## Step H3 — Put it back

When you have finished, set **DAC step** back to **255**.

## What we will learn

- Whether the panel voltage follows the step at all, and in which direction.
- Whether **Panel target** matches your measurements — if it is consistently out by the same
  proportion, our arithmetic has one wrong number in it, which is easy to correct.
- Where it stops responding. We expect the top of the range to be unreachable, and this shows
  whether that is so and by how much.
- Whether the battery voltage rises as you go towards 0, which is what "more charging current"
  should look like.

**If the panel voltage does not change at all** no matter what you type: tell us before doing
anything else. Either the connection to the charge circuit is not what we think it is, or that
part of the board works differently on your version.

---

# Part I — Letting it charge by itself

Only do this **after** Part H, and only if Part H's numbers looked sensible. Until you switch this
on, the board does not charge on its own at all.

## What it will do

Every five minutes it briefly stops charging, measures the solar panel's voltage with nothing
drawing from it, and then asks for about 80% of that — which for most panels is close to the
voltage that gives the most power. In between, it holds that setting. It stops charging when the
battery reaches the **Charge end** voltage, and starts again when the battery has fallen 0.2 V
below it.

It will also stop, and stay stopped, if either the panel or the battery reading goes missing.

## Step I1 — Set the battery type

In the **Charge Control** section, set **Battery type** to match your battery:

| Type | Enter | Charge end voltage it sets |
|---|---|---|
| AGM | 0 | 14.10 V |
| GEL | 1 | 14.10 V |
| Flooded (wet, with caps you can open to add water) | 2 | 14.40 V |
| LiFePO4 / Lithium | 3 | 14.20 V |

Choosing a type fills in **Charge end** for you. You can then change **Charge end** yourself if
you have been told a different figure for your battery — your value will be kept.

**If you are not sure what battery you have, stop and ask.** Charging a battery to the wrong
voltage will shorten its life, and in the worst case can make a sealed battery vent gas.

**One thing to know:** this version does **not** yet adjust the charge voltage for how warm the
battery is, which a full charge controller does. A battery that gets hot should be charged to a
slightly lower voltage. If your battery lives somewhere hot, set **Charge end** about 0.3 V lower
than the table says, and tell us the temperature it reaches.

## Step I2 — Switch it on

Set **Automatic** to on.

## Step I3 — Watch what it says it is doing

The **State** line tells you what it is doing in one word:

| State | Meaning |
|---|---|
| `manual` | Automatic is off; it is using the number you typed |
| `sweeping` | Measuring the panel with nothing drawing from it — lasts one cycle |
| `tracking` | Charging at the voltage it worked out |
| `dark` | The panel has nothing useful to give |
| `full` | The battery has reached the charge-end voltage |
| `no reading` | A sensor has stopped reporting. It has stopped charging on purpose |

**Please record, over one sunny day:**

| Time | State | Open circuit (V) | Panel target (V) | Panel measured (V) | Battery (V) |
|---|---|---|---|---|---|
| mid-morning | | | | | |
| midday | | | | | |
| mid-afternoon | | | | | |
| after sunset | | | | | |

**What we expect:** `tracking` for most of the day, `dark` after sunset, and the measured panel
voltage close to **Panel target**. If the battery gets full you will see `full`.

## Step I4 — Check it stops

This checks the most important safety behaviour. With the sun on the panel and the state showing
`tracking`, **disconnect the wire from the solar panel voltage sensor** — or if that is not easy,
tell us and we will suggest another way.

**You should see:** the state changes to `no reading` within a minute, and charging stops.

Reconnect it. Within a minute it should go back to `tracking`.

## If anything looks wrong

Set **Automatic** back to off. That returns control to you and the board goes to its gentlest
setting. Nothing is damaged by leaving it off.
