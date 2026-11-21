import pcbnew
PCB = '../../daughter/irrigation_daughter.kicad_pcb'
b = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(PCB, b); print('filled')
