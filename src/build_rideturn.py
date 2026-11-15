import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
RT = 0x5B7740
def build():
    a = Asm(RT)
    a.emit('lui', 't9', 0x3B)
    a.emit('lw', 't8', -0x30C0, 't9')        # Angelus +0x20
    a.emit('addiu', 't7', 'zero', 5)
    a.emit('bne', 't8', 't7', 'OUT'); a.emit('nop')
    a.emit('lw', 't8', -0x2D3C, 't9')        # Angelus +0x3A4
    a.emit('addiu', 't7', 'zero', 2)
    a.emit('bne', 't8', 't7', 'OUT'); a.emit('nop')
    a.emit('lw', 't7', 0x2898, 't5')         # digital buttons (t5 = 0x340000)
    a.emit('andi', 't7', 't7', 0x1000)       # Triangle
    a.emit('beq', 't7', 'zero', 'OUT')
    a.emit('lui', 't8', 0xFFCF)
    a.emit('ori', 't8', 't8', 0xFFFF)
    a.emit('and', 's0', 's0', 't8')          # clear the dodge-difference bits 0x300000
    a.emit('lui', 't9', 0x300)
    a.emit('or', 's0', 's0', 't9')           # hold both dodges 0x1000000 | 0x2000000
    a.label('OUT')
    a.emit('j', 0x3409E8)
    a.emit('nop')
    return a
a = build()
p = [(RT + 4 * i, w) for i, w in enumerate(a.assemble())]
p += [(0x3409BC, 0x11C0000D), (0x3409F4, 0x08000000 | (RT >> 2)), (0x3409F8, 0)]
for ad, w in p: print('patch=1,EE,%08X,word,%08X' % (ad, w))
