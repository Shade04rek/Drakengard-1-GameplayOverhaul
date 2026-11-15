import sys, struct
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
FILT = 0x5AF000
FA = 0x5AF0A0
VY, VP, APPLIED = 0xF1F0, 0xF1F4, 0xF1F8      # words 005AF1F0.. (lui 0x5B: 0x5B0000 - 0x0E10 = 005AF1F0)
SMOOTH = 0.25                                  # share of the change in turn speed taken per frame
def fbits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def off(x): return x - 0x10000                 # 005AFxxx from lui 0x5B
def build():
    a = Asm(FILT)
    # in: f6 = yaw step, f7 = pitch step asked for this frame; t8 = 1 on the behind-the-camera path
    a.emit('lui', 't0', 0x5B)
    b = fbits(SMOOTH); a.emit('lui', 't9', b >> 16)
    if b & 0xFFFF: a.emit('ori', 't9', 't9', b & 0xFFFF)
    a.emit('mtc1', 't9', 'f14')
    for reg, slot in (('f6', VY), ('f7', VP)):
        a.emit('lwc1', 'f15', off(slot), 't0')
        a.emit('sub.s', reg, reg, 'f15'); a.emit('mul.s', reg, reg, 'f14'); a.emit('add.s', reg, reg, 'f15')
        a.emit('swc1', reg, off(slot), 't0')
    a.emit('ori', 't1', 'zero', 1); a.emit('sw', 't1', off(APPLIED), 't0')
    a.emit('lui', 't0', 0x14); a.emit('lwc1', 'f15', -0x1AC8, 't0'); a.emit('add.s', 'f15', 'f15', 'f6')
    a.emit('swc1', 'f15', -0x1AC8, 't0')                              # orbit yaw W 0013E538
    a.emit('lui', 't0', 0x3A); a.emit('ori', 't0', 't0', 0xDAC0)
    a.emit('lwc1', 'f15', 0x180, 't0'); a.emit('add.s', 'f15', 'f15', 'f7'); a.emit('swc1', 'f15', 0x180, 't0')   # pitch offset
    a.emit('bne', 't8', 'zero', 'BEH'); a.emit('nop')
    a.emit('j', 0x34246C); a.emit('nop')                              # normal path: on to the dot drawing
    a.label('BEH')
    a.emit('j', 0x342544); a.emit('nop')                              # behind path: as before
    return a
def build_fa():
    a = Asm(FA)
    a.emit('mov.s', 'f6', 'f14')                                      # the behind-the-camera swing
    a.emit('mtc1', 'zero', 'f7')
    a.emit('j', FILT); a.emit('ori', 't8', 'zero', 1)
    return a
def patches():
    p = [(FILT + 4 * i, w) for i, w in enumerate(build().assemble())]
    p += [(FA + 4 * i, w) for i, w in enumerate(build_fa().assemble())]
    p += [(0x3421CC, 0x08000000 | (FA >> 2)), (0x3421D0, 0)]          # behind path -> FA
    p += [(0x342448, 0x08000000 | (FILT >> 2)), (0x34244C, 0x0000C02D)]  # normal path -> FILT, delay: daddu t8,zero,zero
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
