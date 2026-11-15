import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
FW = 0x5AF500
# roll mode FUN_00173E38, first frame: the movement vector Caim +0x300 (s0) is copied from the right axis +0x590 at
# 00173F2C..00173F50 (w = 1.0 at +0x30C), then negated for a left roll (00173F54..00173F6C); both paths reach 00173F74
# after lw v0,0(s1). 00173F50 (swc1 f0,0x8(s0)) -> j FW, the lh v0,0x690(s3) behind it runs in the delay slot.
def build():
    a = Asm(FW)
    a.emit('lwc1', 'f0', 0x5B0, 's3'); a.emit('swc1', 'f0', 0x0, 's0')     # forward axis x
    a.emit('mtc1', 'zero', 'f0'); a.emit('swc1', 'f0', 0x4, 's0')
    a.emit('lwc1', 'f0', 0x5B8, 's3'); a.emit('swc1', 'f0', 0x8, 's0')     # forward axis z
    a.emit('lw', 'v0', 0, 's1')
    a.emit('j', 0x173F74); a.emit('nop')
    return a
def patches():
    return [(FW + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x173F50, 0x08000000 | (FW >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
