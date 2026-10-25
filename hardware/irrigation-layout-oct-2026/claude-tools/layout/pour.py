"""KiCad python: GND pours on both layers over the whole board, fill, save. Then report track/via counts."""
import pcbnew, json
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
gnd = b.FindNet('GND')
e = b.GetBoardEdgesBoundingBox()
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(gnd)
    o = z.Outline(); o.NewOutline()
    for x, y in ((e.GetX(), e.GetY()), (e.GetRight(), e.GetY()), (e.GetRight(), e.GetBottom()), (e.GetX(), e.GetBottom())):
        o.Append(x, y)
    z.SetMinThickness(mm(0.25)); z.SetThermalReliefGap(mm(0.25)); z.SetThermalReliefSpokeWidth(mm(0.35))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    try: z.SetLocalClearance(mm(0.3))
    except Exception as ex: print('clearance', ex)
    z.SetAssignedPriority(0)
    b.Add(z)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('poured and filled')
