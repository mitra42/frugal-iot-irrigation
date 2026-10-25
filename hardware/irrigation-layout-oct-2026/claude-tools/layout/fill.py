import pcbnew
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(PCB, b); print('filled')
