"""KiCad python, one job: silkscreen pin names beside the two connectors a person wires by hand (D2) - J1 to the
host (GND SDA SCL 3V3 V12, so the cable can be checked against the host's J2) and J3 for the OLED - and the
title. Run after post_route.sh (silk.py places the references first); DRC is the check."""
import pcbnew
PCB = '../../daughter/irrigation_daughter.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; O = 50.0
pads = {(f.GetReference(), p.GetNumber()): p.GetPosition() for f in b.GetFootprints() for p in f.Pads()}
old = [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT']   # the title, re-placed by addtext.py afterwards
for d in old: b.Remove(d)
def txt(s, x, y, ang=0):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.12)); t.SetTextAngleDegrees(ang)
    t.SetPosition(pcbnew.VECTOR2I(int(x), int(y))); b.Add(t)
for n, s in zip('12345', ('V12', '3V3', 'SCL', 'SDA', 'GND')):     # below J1's body, reading upwards
    p = pads[('J1', n)]; txt(s, p.x, mm(O + 9.9), 90)
for n, s in zip('1234', ('GND', 'VCC', 'SCL', 'SDA')):             # below J3's pins
    p = pads[('J3', n)]; txt(s, p.x, mm(O + 6.3), 90)
pcbnew.SaveBoard(PCB, b); print('labels placed')
