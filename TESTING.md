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

# Part G — Solar charging (not yet — for information)

The solar charge control is not in the software yet. When it is, these steps will be added:

- **G1** Measure the solar panel voltage and compare with the board's reading, as in Part E.
- **G2** Identify which temperature sensor is which (there may be up to three).
- **G3** The important one: we will add a control that lets you set the charger by hand to about
  ten different settings. At each setting you record the panel voltage and the battery voltage.
  That table of twenty numbers, taken on one sunny day, tells us more about the board than
  anything else in this document.

If you are able to answer the questions in [HARDWARE-QUESTIONS.md](HARDWARE-QUESTIONS.md) before
then, it will save a lot of guessing.
