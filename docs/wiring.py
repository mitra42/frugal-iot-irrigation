"""Wiring diagrams for README.md - one per board that you wire up yourself.
Run: python3 docs/wiring.py   (writes docs/wiring_*.svg and .png)
Uses the wiring-diagrams skill (~/.claude/skills/wiring-diagrams). The three Frugal-IoT boards are drawn from
their KiCad layouts by its kicad_part.py --populated, so they look as assembled and their silkscreen is
exactly what is printed; the S2 Mini is a Fritzing part.

Layout rule, from the skill: pins that run straight across in the same order never cross. Each layout below
was chosen for that, and the crossings left are the ones no arrangement avoids - each is noted where it is drawn.
"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/wiring-diagrams/scripts"))
from wiring import Diagram
HERE = os.path.dirname(os.path.abspath(__file__))
MM = 9.0                         # pixels per mm for the Frugal-IoT boards, so they are drawn to one scale
VALVE, BATT, PANEL, MPPT = "#4a5a6a", "#2b2b2b", "#1b2f5a", "#3b4a2a"
DAUGHTER_VALVES = [("V1+", "V1"), ("V2+", "V2"), ("V3+", "V3"), ("P+", "P")]
OLED_HDR = ["OLED_GND", "OLED_VCC", "OLED_SCL", "OLED_SDA"]

def valves(d, board, terms, y, labels=("Valve 1", "Valve 2", "Valve 3", "Pump")):
    """A valve (or the pump) under each 2-way terminal: its + to pin 1 (+12V), its other lead to pin 2,
    which the board's MOSFET switches to ground."""
    for (p1, p2), name in zip(terms, labels):
        a, b = board[p1], board[p2]
        pitch = b[0] - a[0]
        m = d.module(a[0] + pitch / 2 - 43, y, name, ["+", "-"], side="top", pitch=pitch, w=86, h=74,
                     fill=VALVE, note="12 V DC")
        d.wire(a, m["+"], "power")
        d.wire(b, m["-"], "signal2")

def power(d, x, plus, minus, usb=None, probe=None):
    """Solar panel -> MPPT charge controller -> 12 V battery, in a column at x, the battery level with the
    board's 12 V terminal (plus, minus). Returns (mppt, battery) so other leads can be taken from them:
    usb="left" or "right" adds the controller's USB socket on that side; probe=True adds a lead from the
    battery's + on its left, for an RS485 probe's supply."""
    bh, gap = 120, 60
    by = (plus[1] + minus[1]) / 2 - bh / 2
    my = by - gap - 100
    py = my - gap - 80
    pan = d.module(x, py, "Solar panel", ["+", "-"], side="bottom", pitch=60, w=200, h=80, fill=PANEL,
                   note="12 V nominal")
    mppt = d.module(x, my, "MPPT charger", ["PV+", "PV-"], side="top", pitch=60, w=200, h=100, fill=MPPT,
                    note="solar charge controller", more={"bottom": ["BAT+", "BAT-"], **({usb: ["USB"]} if usb else {})})
    bat = d.module(x, by, "12 V battery", ["+", "-"], side="right", pitch=abs(minus[1] - plus[1]), w=200, h=bh,
                   fill=BATT, more={"top": ["+#t", "-#t"], **({"left": ["+#l"]} if probe else {})})
    d.wire(pan["+"], mppt["PV+"], "power")
    d.wire(pan["-"], mppt["PV-"], "ground")
    d.wire(mppt["BAT+"], bat["+#t"], "power")
    d.wire(mppt["BAT-"], bat["-#t"], "ground")
    d.wire(bat["+"], plus, "power")
    d.wire(bat["-"], minus, "ground")
    return mppt, bat

def oled_above(d, board, pins, y):
    """An SSD1306 OLED module above a 4-pin header (GND, VCC, SCL, SDA left to right)."""
    xs = [board[p][0] for p in pins]
    m = d.module((xs[0] + xs[-1]) / 2 - 85, y, "OLED 128x64", ["GND", "VCC", "SCL", "SDA"], side="bottom",
                 pitch=xs[1] - xs[0], w=170, note="SSD1306, I2C")
    for p, q, k in zip(pins, ["GND", "VCC", "SCL", "SDA"], ["ground", "power", "signal", "signal2"]):
        d.wire(m[q], board[p], k)

def oled_right(d, board, pins, x, ymid):
    """An OLED module to the right of a 4-pin header (GND, VCC, SCL, SDA left to right), its pins on its left
    side in the same order top to bottom: each wire runs left, then drops onto its pin, none crossing."""
    m = d.module(x, ymid - 65, "OLED 128x64", ["GND", "VCC", "SCL", "SDA"], side="left", pitch=23, w=170, h=130,
                 note="SSD1306, I2C")
    for p, q, k in zip(pins, ["GND", "VCC", "SCL", "SDA"], ["ground", "power", "signal", "signal2"]):
        d.wire(m[q], board[p], k)

def footnote(d, x, y):
    d.note(x, y, "Blue at a valve: the side the\nboard switches to ground.", size=13)

# ---------------------------------------------------------------- b: Irrigation V0.2 board
def irrigation_v02():
    d = Diagram(1560, 1080, "Frugal-IoT Irrigation V0.2 board",
                "env frugal_irrigation_v02. Valves 1-3 and the pump on J11-J14; RS485 soil probes on J10, powered from it.")
    b = d.board("frugal_irrigation_v02", x=330, y=260, width=105 * MM)
    power(d, 40, b["+12V"], b["GND_IN"])
    valves(d, b, DAUGHTER_VALVES, 260 + 67 * MM + 40)
    oled_above(d, b, OLED_HDR, 130)
    # RS485 probe: J10 reads GND, B, A, 5V_SW left to right (it faces the top edge, pin 1 on the right)
    order = ["RS_GND", "B", "A", "5V_SW"]
    xs = [b[p][0] for p in order]
    pr = d.module((xs[0] + xs[-1]) / 2 - 110, 110, "RS485 soil probe", ["GND", "B", "A", "V+"], side="bottom",
                  pitch=xs[1] - xs[0], w=220, h=86, note="Modbus; slave id 2, 3, 4")
    for p, q, k in zip(order, ["GND", "B", "A", "V+"], ["ground", "signal2", "signal", "power"]):
        d.wire(pr[q], b[p], k)
    d.note(330 + 105 * MM - 200, 120, "Further probes join the\nsame four wires (a bus).", size=13)
    d.note(40, 175, "The board runs from the 12 V\nbattery: no USB power needed.", size=13)
    footnote(d, 330 + 4 * 10.16 * MM + 300, 260 + 67 * MM + 80)
    d.save(os.path.join(HERE, "wiring_irrigation_v02"))

# ---------------------------------------------------------------- c: sensor board + daughter
def sensor_daughter():
    d = Diagram(1700, 1300, "Frugal-IoT sensor board V0.2 + irrigation daughter board",
                "env sensor_v02_daughter. Sensor J2 pins 1-4 and 9 to daughter J1; valves 1-3 and the pump on daughter J4-J7.")
    DX, DY, SX, SY = 300, 640, 700, 170
    db = d.board("irrigation_daughter", x=DX, y=DY, width=105 * MM)
    sb = d.board("frugal_iot_sensor_v02", x=SX, y=SY, width=69 * MM)
    # host J2 -> daughter J1: J1 reads GND, SDA, SCL, 3V3, V12 left to right, the host's J2 1-4 and 9 top to bottom
    for hp, dp, k in (("GND", "GND", "ground"), ("SDA", "SDA", "signal2"), ("SCL", "SCL", "signal"),
                      ("3V3_SW", "3V3", "power"), ("S2", "V12", "signal3")):
        d.wire(sb[hp], db[dp], k)
    d.note(80, 300, "5-wire cable: sensor J2 pins\n1 GND, 2 SDA, 3 SCL, 4 3V3, and\n9 S2 (V12 from the daughter)", size=13)
    mppt, bat = power(d, 80, db["+12V"], db["GND_IN"], usb="left", probe=True)
    # RS485 probe on the sensor's J3, which reads B, A, GND top to bottom (pin 1 at the bottom). Its supply
    # is the 12 V battery: the sensor board has only 3.3 V on J3.
    ys = [sb[p][1] for p in ("B", "A", "RS_GND")]
    pr = d.module(SX + 69 * MM + 70, (ys[0] + ys[-1]) / 2 - 75, "RS485 soil probe", ["B", "A", "GND"], side="left",
                  pitch=ys[1] - ys[0], w=200, h=150, note="Modbus; slave id 2, 3, 4", more={"top": ["V+"]})
    for p, q, k in (("B", "B", "signal2"), ("A", "A", "signal"), ("RS_GND", "GND", "ground")):
        d.wire(sb[p], pr[q], k)
    # Two leads go from the left-hand column right round the top of the sensor board: 12 V to the probe and
    # USB to the sensor. They cross once, where the 12 V drops onto the probe - inevitable, since the USB
    # has to come back down the far side of the probe.
    d.wire(bat["+#l"], pr["V+"], "power", via=["x=28", "y=96"])
    usb = sb["USB"]
    d.wire(mppt["USB"], usb, "power", via=["x=46", "y=114", f"x={SX + 69 * MM + 300}", f"y={SY + 42 * MM + 18}", f"x={usb[0]}"])
    d.note(SX + 69 * MM - 330, SY + 42 * MM + 40, "USB cable: 5 V from the MPPT's USB socket", size=13)
    oled_right(d, db, OLED_HDR, DX + 105 * MM + 30, DY + 25)
    valves(d, db, DAUGHTER_VALVES, DY + 47 * MM + 40)
    footnote(d, DX + 4 * 10.16 * MM + 300, DY + 47 * MM + 80)
    d.save(os.path.join(HERE, "wiring_sensor_daughter"))

# ---------------------------------------------------------------- a: S2 Mini + daughter
def s2_daughter():
    d = Diagram(1560, 1320, "Lolin S2 Mini + irrigation daughter board",
                "env s2_mini_daughter. The tank sender (GPIO6) and the probes' A/B wiring (as on the V0.2 board) not shown.")
    DX, DY, SX, SY, S2W = 380, 720, 300, 130, 300
    db = d.board("irrigation_daughter", x=DX, y=DY, width=105 * MM)
    sb = d.board("lolin_s2_mini", x=SX, y=SY, width=S2W, pin_labels=["35", "33", "18", "16", "GND", "3", "3V3"])
    # I2C on GPIO16/18 and the RS485 UART on GPIO33/35 - the other way round from the S2's usual I2C pins -
    # so that, on the right-hand header, the RS485 pair (going right, to the transceiver) is above the I2C
    # wires (going down, to J1), and no wire crosses another.
    d.wire(sb["GND"], db["GND"], "ground")
    d.wire(sb["16"], db["SDA"], "signal2")
    d.wire(sb["18"], db["SCL"], "signal")
    # RS485 transceiver to the right: DI from TX (GPIO35), RO to RX (GPIO33)
    tx = DX + 105 * MM - 470
    t = d.module(tx, (sb["35"][1] + sb["33"][1]) / 2 - 55, "RS485 module", ["DI", "RO"], side="left",
                 pitch=sb["33"][1] - sb["35"][1], w=210, h=110, note="3.3 V, auto direction",
                 more={"top": ["VCC"], "bottom": ["GND"], "right": ["A", "B"]})
    d.wire(sb["35"], t["DI"], "signal3")
    d.wire(sb["33"], t["RO"], "signal")
    # 3V3 and GPIO3 (V12) leave the left-hand header, go over the top and round the far side of the
    # transceiver, and come back to J1's two right-hand pins. They cross once: on this side GPIO3 is above
    # 3V3, and J1 wants V12 to the right of 3V3. The transceiver's VCC tees off the 3V3 lead.
    far = tx + 210 + 60
    d.wire(sb["3V3"], db["3V3"], "power", via=["x=262", "y=96", f"x={far + 18}", f"y={t.box[1] + 110 + 70}"])
    d.wire(sb["3"], db["V12"], "signal3", via=["x=280", "y=114", f"x={far}", f"y={t.box[1] + 110 + 52}"])
    d.junction(far + 18, t["VCC"][1] - 30)
    d.wire((far + 18, t["VCC"][1] - 30), t["VCC"], "power")
    # Its ground tees off the S2 ground lead, crossing SDA and SCL on the way
    gx = db["GND"][0]
    d.junction(gx, sb["GND"][1])
    d.wire((gx, sb["GND"][1]), t["GND"], "ground", via=[f"x={t['GND'][0]}"])
    d.note(far + 40, t.box[1] + 40, "A, B to the probes,\nwhich need their own\n5-30 V supply", size=13)
    d.note(760, 440, "S2 Mini: SDA = GPIO16, SCL = GPIO18,\nV12 (the battery) on GPIO3.\n"
           "The S2 has no I2C pull-ups: the\ndaughter board's R19/R20 provide them.", size=13)
    mppt, bat = power(d, 40, db["+12V"], db["GND_IN"], usb="right")
    # USB from the charger to the S2 Mini's USB-C, at the middle of its bottom edge
    ux, uy = SX + S2W * 0.465, SY + sb.box[3] - 8
    d.wire(mppt["USB"], (ux, uy), "power")
    d.note(ux + 12, uy + 46, "USB cable: 5 V from\nthe MPPT's USB socket", size=13)
    oled_right(d, db, OLED_HDR, DX + 105 * MM + 30, DY + 25)
    valves(d, db, DAUGHTER_VALVES, DY + 47 * MM + 40)
    footnote(d, DX + 4 * 10.16 * MM + 300, DY + 47 * MM + 80)
    d.save(os.path.join(HERE, "wiring_s2_daughter"))

if __name__ == "__main__":
    irrigation_v02()
    sensor_daughter()
    s2_daughter()
