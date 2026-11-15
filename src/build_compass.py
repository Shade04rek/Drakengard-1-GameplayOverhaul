import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
VX = 0x5B8240
K = 139            # extra x factor for the compass, /256 (0.54: measured disc 117 x 63 px on screen)
CC = 0xF00         # compass centre relative to t3 (screen centre) after the 80 px edge shift: 480 px + 80 px, x16 units

def build():
    a = Asm(VX)
    # entered from 003228C4 (j VX); its delay slot 003228C8 (addu t1,t1,t4: the edge shift) already ran
    a.emit('addu', 't1', 't1', 't3')           # the replaced instruction: back to absolute x16
    a.emit('ori', 't2', 'zero', 0x500)
    a.emit('bne', 't4', 't2', 'BACK')          # only packets shifted right ...
    a.emit('nop')
    a.emit('lui', 't2', 0x32)
    a.emit('lw', 't2', 0x1DD8, 't2')           # ... in the upper area (packet min y below the bottom-row line 0x8B10): the compass and its blips
    a.emit('ori', 't5', 'zero', 0x8B10)
    a.emit('sltu', 't2', 't2', 't5')
    a.emit('beq', 't2', 'zero', 'BACK')
    a.emit('nop')
    a.emit('addiu', 't5', 't3', CC)            # compass centre
    a.emit('subu', 't1', 't1', 't5')
    a.emit('ori', 't2', 'zero', K)
    a.emit('mult', 't1', 't2')
    a.emit('mflo', 't1')
    a.emit('sra', 't1', 't1', 8)               # (x - centre) * K / 256
    a.emit('addu', 't1', 't1', 't5')
    a.label('BACK')
    a.emit('j', 0x3228CC)
    a.emit('nop')
    return a
def patches():
    a = build()
    return [(a.base + 4 * i, w) for i, w in enumerate(a.assemble())] + [(0x3228C4, 0x08000000 | (VX >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('%08X %08X' % (ad, w))
