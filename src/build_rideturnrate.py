import sys, struct
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
TR = 0x5B7790
FACTOR = 1.5                       # vanilla 0.75
def build():
    bits = struct.unpack('<I', struct.pack('<f', FACTOR))[0]
    assert bits & 0xFFFF == 0
    a = Asm(TR)
    a.emit('lui', 'at', 0x34)
    a.emit('lw', 'at', 0xDFC, 'at')          # aerial marker
    a.emit('bne', 'at', 'zero', 'AER')
    a.emit('lui', 'at', 0x3F40)              # delay slot: vanilla 0.75
    a.emit('lui', 'at', bits >> 16)          # ground stage: faster turn
    a.label('AER')
    a.emit('mtc1', 'at', 'f2')
    a.emit('j', 0x1C46F0)
    a.emit('nop')
    return a
if __name__ == '__main__':
    a = build()
    for i, w in enumerate(a.assemble()): print('patch=1,EE,%08X,word,%08X' % (TR + 4 * i, w))
    print('patch=1,EE,001C46E8,word,%08X' % (0x08000000 | (TR >> 2)))
