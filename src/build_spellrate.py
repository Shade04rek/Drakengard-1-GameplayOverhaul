import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
BASE = 0x5AF100
def triple(a, r):
    a.emit('srl', 'at', r, 1); a.emit('addu', r, r, 'at')            # r * 1.5
def build():
    a = Asm(BASE)
    entries = {}
    for r in ('t0', 'a3'):                                            # jal sites: r * 3, the store in the jr delay slot
        a.label('R_' + r); triple(a, r); a.emit('jr', 'ra'); a.emit('sh', r, 0x174, 's0')
    # 0017D5F4 (sh v0,0x170 before sh t0,0x174 / beq): j C5, the sh t0 runs unscaled in its delay slot
    a.label('C5')
    a.emit('sh', 'v0', 0x170, 's0'); triple(a, 't0'); a.emit('sh', 't0', 0x174, 's0')
    a.emit('j', 0x17D6F8); a.emit('sw', 'v1', 0x2F8, 's0')
    # 0017D6C8 (beq zero,zero,0017D6F8 with sh v1,0x174 in its delay slot): j C6
    a.label('C6')
    triple(a, 'v1'); a.emit('sh', 'v1', 0x174, 's0')
    a.emit('j', 0x17D6F8); a.emit('nop')
    return a
def patches():
    a = build(); ws = a.assemble()
    lab = a.labels
    p = [(BASE + 4 * i, w) for i, w in enumerate(ws)]
    jal = lambda t: 0x0C000000 | (t >> 2); j = lambda t: 0x08000000 | (t >> 2)
    p += [(0x17D3D0, jal(lab['R_t0'])), (0x17D548, jal(lab['R_a3'])), (0x17D560, jal(lab['R_a3'])),
          (0x17D5F4, j(lab['C5'])), (0x17D6C8, j(lab['C6']))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
