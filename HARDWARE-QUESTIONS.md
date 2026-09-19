# Questions for whoever has the FF-ESP32-OpenMPPT board

We have added support for a board we do not have. Everything below is something you can see or
measure - none of it needs any knowledge of the software.

**Photographs are very welcome.** A clear photograph of the whole board, plus close-ups of
anything a question mentions, often answers several questions at once.

Please number your answers to match. 

Posting to a new issue on the repo is probably the best way, though email to support@naturalinnovation.org 

---

## 1. Which board is it?

Look on the board for a printed version number. It is usually near an edge, or near the name of
the board, and looks like `v1.0`, `v1.1` or `v1.2`.

- What does it say?
- If there is no version number, please photograph both sides of the board.

**Why we ask:** three versions of this board exist and they behave differently. We currently
assume the newest.

---

## 2. The part marked D6

Find the printed label **D6** on the board. It is near where the solar panel wires connect.

Which of these do you see? Please also photograph it closely.

- **(a)** A small black or grey component with a stripe or line printed at one end. That is a
  diode.
- **(b)** No component — instead, a short piece of wire, or a blob of solder, joining the two
  metal pads to each other.
- **(c)** Two bare metal pads with nothing between them and nothing joining them.

**Why we ask:** if the diode is there, the board loses about 0.3 V of the panel's voltage, and our
software must add that back. If it has been replaced by a wire, it must not.

---

## 3. The temperature sensors

This board can have up to three temperature sensors. They are small components, often in a metal
tube on the end of a cable, or a small black rectangle soldered flat to the board.

- How many can you find?
- For each one: where is it? On the board itself, attached to the metal heatsink, clipped to the
  battery, or hanging free in the air?
- Please photograph each one and where it is attached.

**Why we ask:** the software needs to know which reading is the battery and which is the board, and
they look identical electrically. Physical position is the only way to tell.

---

## 4. Is there a temperature sensor built into the board itself?

Separate from question 3. Look for two very small components side by side, close to the large metal
heatsink, labelled something like **D1 D2** or **T1**, with a resistor beside them.

- Is there anything like that? Photograph it.

**Why we ask:** there are two possible ways this board measures its own heat, and we do not know
which one your board uses. We only want to include the right one.

---

## 5. What is connected to the load output?

There is one output meant for a permanent load, separate from the valves.

- Is anything connected to it? What?
- We have been told it is often a WiFi router. Is that the case here?

**Why we ask:** the software can switch this output off when the battery is low, and can restart
it if the internet stops working. Both are only sensible if we know what is plugged in.

---

## 6. Is there a USB socket on the board?

- Is there a USB socket meant for **supplying power to something else** (as opposed to the one you
  plug into a computer)?
- If yes, is anything plugged into it?

**Why we ask:** on the original design this socket shares a connection with one of the irrigation
valves — you can have the third valve, or the USB socket, but not both. We need to know which one
you need.

---

## 7. The tank sensor connection

- Is a water tank sensor connected? What kind — a float on an arm, a float on a rod, something
  else?
- Which terminal on the board is it connected to? Please photograph it, including any printed
  label beside that terminal.

**Why we ask:** the original documentation is contradictory about which connection the tank sensor
uses. One note says it is a temperature input. We would rather know than guess.

---

## 8. The battery and the solar panel

From the labels on them:

- **Battery:** what type? The label may say AGM, GEL, Flooded (sometimes "wet"), or LiFePO4 /
  Lithium. What capacity, in Ah?
- **Solar panel:** the label on the back usually lists several numbers. We need **Voc** (or "open
  circuit voltage"), **Vmp** or **Vmpp** (or "voltage at maximum power"), and the **watts**.
- Please photograph both labels.

**Why we ask:** different battery types must be charged to different voltages. Charging one type to
another type's voltage will damage it, sometimes quickly.

---

## 9. What can you measure, and for how long?

- Do you have a multimeter? (We assume yes.)
- Can you leave the system running for several days and come back to it, or do you only have it for
  a short time?
- Is there a sunny place to test, and roughly what hours does the sun reach the panel?

**Why we ask:** some of the checks need readings taken at different times of day, and some need
none of that. Please still tell us your answers — but **do not wait for us before starting.** Find
your situation in this table and go straight to that plan.

| Your situation | Your plan |
|---|---|
| An afternoon with the board, sun or no sun | [docs/plan-bench.md](docs/plan-bench.md) |
| Sun on the panel, a multimeter, an hour and a half | [docs/plan-sunny-session.md](docs/plan-sunny-session.md) — do the bench plan first if you can |
| The board can stay somewhere sunny for three days or more | [docs/plan-long-run.md](docs/plan-long-run.md) — after both of the above |
| No multimeter | [docs/plan-bench.md](docs/plan-bench.md), skipping Part E. The two tests that need a meter are the ones we most need — there is a note at the end of that plan about what it costs us |

Each plan is a short list pointing into [TESTING.md](TESTING.md), which has the actual steps. If
none of the four describes your situation, tell us what you have got and we will write one that
does.

---

## 10. What happens to the outputs when the board is asleep?

This one needs a measurement rather than a look, a multimeter, and a **different build of the
software**. **It can wait until you have done the rest** — and you do not need anything from us to
start it: the software is on a branch called `sleep-test`, and
[docs/sleep-test.md](docs/sleep-test.md) says how to build it, how to tell when the board is
asleep, and exactly what to measure.

The board can be told to sleep when the battery is low, so that the solar panel gets a chance to
recharge it. But while an ESP32 sleeps, its output pins are normally *released* — they stop being
driven — and we do not know what this board does then. The original software sets pin 14 with a
"pull-up", which if it still applies while asleep would switch the load **on** at exactly the
moment we were trying to save power.

That build sleeps on a repeating cycle — five minutes awake, two minutes asleep — so nothing has to
be triggered or timed. It asks for six readings: the pin 14 output terminal — the page calls it
**Pump**, the original software uses it as the load switch — switched on and then switched off,
each measured while awake and then again while asleep, and the solar panel voltage the same way.

**Why we ask:** if sleeping turns the load back on, or stops the battery charging, then sleeping
to save power makes things worse rather than better, and we will leave the feature switched off.

---

## 11. Anything that surprises you

If anything on the board looks damaged, modified, hand-soldered, or simply different from what
these questions describe, please tell us and photograph it. A board that has been repaired or
changed is very common and completely fine — but only if we know.
