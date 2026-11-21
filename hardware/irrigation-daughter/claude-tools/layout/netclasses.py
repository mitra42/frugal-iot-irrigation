"""Write net classes + board rules into ../daughter/irrigation_daughter.kicad_pro (JLCPCB 2-layer capable)."""
import json, xml.etree.ElementTree as ET
VALVE = [n.get('name') for n in ET.parse('../schematic/out/netlist.xml').getroot().iter('net')
         if any(nd.get('ref') == f'Q{i}' and nd.get('pin') == '3' for nd in n.iter('node') for i in range(1, 9))]
assert len(VALVE) == 8, VALVE
p = '../../daughter/irrigation_daughter.kicad_pro'
d = json.load(open(p))
def cls(name, clr, w, via=0.6, drill=0.3, dpw=0.2, dpg=0.25, prio=0):
    return {"name": name, "clearance": clr, "track_width": w, "via_diameter": via, "via_drill": drill,
            "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_width": dpw, "diff_pair_gap": dpg,
            "diff_pair_via_gap": 0.25, "wire_width": 6, "bus_width": 12, "line_style": 0,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "pcb_color": "rgba(0, 0, 0, 0.000)", "priority": prio}
d['net_settings'] = {
    "classes": [cls('Default', 0.2, 0.25, prio=2147483647), cls('Power', 0.2, 0.6, via=0.8, drill=0.4, prio=1),
                cls('PowerFine', 0.2, 0.3, via=0.6, drill=0.3, prio=1),
                cls('Valve', 0.3, 1.0, via=1.0, drill=0.5, prio=0)],
    "meta": {"version": 4},
    "net_colors": None,
    "netclass_assignments": None,
    # As the irrigation board (its D82): Valve 1 mm (2 A on 1 oz outer copper, ~10 C rise); +12V Power 0.6 mm,
    # its 3 A path (D1 -> bus -> every terminal) drawn 2 mm by valve_route.py.
    # Valve: the 3 A input path (12V_IN, 12V_FUSED) and each valve output. VALVEn has no label in the schematic,
    # so its KiCad name (Net-(D3-A), ... and one Net-(D10-K)) is read from the netlist: the net on Qn's drain.
    "netclass_patterns": [{"netclass": "Valve", "pattern": n} for n in ['/12V_IN', '/12V_FUSED'] + VALVE] +
        [{"netclass": "Power", "pattern": n} for n in ['GND', '+12V']] +
        [{"netclass": "PowerFine", "pattern": n} for n in ['+3V3_SW']]}
bd = d.setdefault('board', {}).setdefault('design_settings', {})
bd.setdefault('rules', {}).update({"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.5,
    "min_through_hole_diameter": 0.3, "min_hole_to_hole": 0.25, "min_copper_edge_clearance": 0.3,
    "min_hole_clearance": 0.25, "min_silk_clearance": 0.0, "min_text_height": 0.8, "min_text_thickness": 0.08,
    "min_resolved_spokes": 1})
json.dump(d, open(p, 'w'), indent=2)
print('ok')
