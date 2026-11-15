import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
GF = 0x5BAD90
# T2 ground path: 00321A7C lw t9 = ground FOV word (0033F6F8), 00321A88 sw t9 -> 003ADBB0 when non-zero, t7 = 0x3B0000.
# The j 0033EDAC at 00321A8C now goes to GF, which also stores it to the aerial cameras CCamAirLForPlayer / CCamAirHForPlayer
# (003ADD70 / 003ADEC0 = their +0xF0): the ridden Angelus view on the ground after a story stage transition uses them and
# kept the aerial 1.1. Aerial stages never take this path (AFOV writes 1.1 there every frame).
def build():
    a = Asm(GF)
    a.emit('beq', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('sw', 't9', -0x2290, 't7'); a.emit('sw', 't9', -0x2140, 't7')
    a.label('OUT')
    a.emit('j', 0x33EDAC); a.emit('nop')
    return a
def patches():
    return [(GF + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x321A8C, 0x08000000 | (GF >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
