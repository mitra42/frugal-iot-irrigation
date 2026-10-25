import pcbnew, json, sys
b = pcbnew.LoadBoard(sys.argv[1] if len(sys.argv) > 1 else '../../esp32_io_board/esp32_io_board.kicad_pcb')
json.dump([{"ref": f.GetReference(), "pad": p.GetNumber(), "net": str(p.GetNetname()),
            "x": p.GetPosition().x / 1e6, "y": p.GetPosition().y / 1e6} for f in b.GetFootprints() for p in f.Pads()],
          open('out/pads.json', 'w'))
print('ok')
