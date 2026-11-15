import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade--claude-spares-spare-lRXJwn\fc7fa988-ea8f-4fa2-b5eb-1c7f92e06e80\scratchpad')
sys.path.insert(1, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
SUPP1, SUPP2, MAP4 = 0x5B7620, 0x5B7650, 0x5B7680
FLAG = 0x5B7700        # 1 while the extra chapter-map updates run: button presses read as 0
EXTRA = 3              # extra updates per frame: 3 = 4x

def supp(base, fn):
    # entered from fn's first word (j SUPPx); fn's second word (daddu v1,a0,zero) already ran in the delay slot
    a = Asm(base)
    a.emit('lui', 't9', 0x5B)
    a.emit('lw', 't9', 0x7700, 't9')
    a.emit('beq', 't9', 'zero', 'NORM')
    a.emit('nop')
    a.emit('jr', 'ra')
    a.emit('or', 'v0', 'zero', 'zero')      # no buttons pressed during an extra update
    a.label('NORM')
    a.emit('addiu', 'sp', 'sp', -0x10)       # the replaced first instruction
    a.emit('j', fn + 8)
    a.emit('nop')
    return a

def map4():
    a = Asm(MAP4)
    a.emit('addiu', 'sp', 'sp', -0x30)
    a.emit('sw', 'ra', 0x20, 'sp')
    a.emit('sw', 'a0', 0x10, 'sp')
    a.emit('sw', 'a1', 0x14, 'sp')
    a.emit('jal', 0x2D4384)                  # the normal update (reads the buttons)
    a.emit('nop')
    a.emit('beq', 'v0', 'zero', 'DONE')      # 0 = the chapter map finished: no extra calls
    a.emit('nop')
    a.emit('addiu', 't4', 'zero', EXTRA)
    a.emit('sw', 't4', 0x18, 'sp')
    a.emit('lui', 't4', 0x5B)
    a.emit('addiu', 't5', 'zero', 1)
    a.emit('sw', 't5', 0x7700, 't4')         # buttons off
    a.label('LOOP')
    a.emit('lw', 'a0', 0x10, 'sp')
    a.emit('lw', 'a1', 0x14, 'sp')
    a.emit('jal', 0x2D4384)
    a.emit('nop')
    a.emit('beq', 'v0', 'zero', 'END')
    a.emit('nop')
    a.emit('lw', 't4', 0x18, 'sp')
    a.emit('addiu', 't4', 't4', -1)
    a.emit('sw', 't4', 0x18, 'sp')
    a.emit('bne', 't4', 'zero', 'LOOP')
    a.emit('nop')
    a.label('END')
    a.emit('lui', 't4', 0x5B)
    a.emit('sw', 'zero', 0x7700, 't4')       # buttons back on
    a.label('DONE')
    a.emit('lw', 'ra', 0x20, 'sp')
    a.emit('jr', 'ra')
    a.emit('addiu', 'sp', 'sp', 0x30)
    return a

def patches():
    out = []
    for a in (supp(SUPP1, 0x1287F0), supp(SUPP2, 0x128850), map4()):
        out += [(a.base + 4 * i, w) for i, w in enumerate(a.assemble())]
    out += [(0x1287F0, 0x08000000 | (SUPP1 >> 2)), (0x128850, 0x08000000 | (SUPP2 >> 2)),
            (0x1505D4, 0x0C000000 | (MAP4 >> 2)), (FLAG, 0)]
    return out
if __name__ == '__main__':
    for ad, w in patches(): print('%08X %08X' % (ad, w))

