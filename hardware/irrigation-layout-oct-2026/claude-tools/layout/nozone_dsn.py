"""KiCad python, one job: export out/board.dsn from the board WITHOUT its GND pours, for routing a routed board
again (route_patch.sh). The pours would otherwise go to Freerouting as copper and block everything; pour.py puts
them back after the import. The board file itself is left as it is - the zone-less copy is out/nozone.kicad_pcb."""
import pcbnew
b = pcbnew.LoadBoard('../../esp32_io_board/esp32_io_board.kicad_pcb')
zs = list(b.Zones())
for z in zs: b.Remove(z)
pcbnew.SaveBoard('out/nozone.kicad_pcb', b)
print('zones removed', len(zs), 'dsn', pcbnew.ExportSpecctraDSN(b, 'out/board.dsn'))
