"""KiCad python: import out/routed.ses into the board (which already holds the GND fan-out), save."""
import pcbnew, json
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB)
ok = pcbnew.ImportSpecctraSES(b, 'out/routed.ses')
stats = {'import_ok': bool(ok)}
json.dump(stats, open('out/import.json', 'w'))
pcbnew.SaveBoard(PCB, b)
print(stats)
