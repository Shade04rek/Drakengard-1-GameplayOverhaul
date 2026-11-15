import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
WIDE = 0x5BAC00
WIDEN_HI = 0x3F99        # 1.1953: far corners pushed away from their centre (wider and taller culling frustum)
CORNERS = 0x5B6A10       # FRUS scratch copy: apex at 005B6A00, four far corners after it
# FRUS ends with daddu s0,a1,zero / j 0027590C; that j (005B699C) now goes here. Uses only t2, at, f0, f4..f7, f12
# (FRUS already clobbers t0..t2, f0..f6, f12).
def build():
    a = Asm(WIDE)
    a.emit('lui', 't2', 0x5B); a.emit('addiu', 't2', 't2', CORNERS & 0xFFFF)
    a.emit('mtc1', 'zero', 'f4'); a.emit('mov.s', 'f5', 'f4'); a.emit('mov.s', 'f6', 'f4')
    for i in range(4):
        for k, fs in enumerate(('f4', 'f5', 'f6')):
            a.emit('lwc1', 'f0', 16 * i + 4 * k, 't2'); a.emit('add.s', fs, fs, 'f0')
    a.emit('lui', 'at', 0x3E80); a.emit('mtc1', 'at', 'f7')                  # 0.25
    for fs in ('f4', 'f5', 'f6'): a.emit('mul.s', fs, fs, 'f7')
    a.emit('lui', 'at', WIDEN_HI); a.emit('mtc1', 'at', 'f12')
    for i in range(4):
        for k, fs in enumerate(('f4', 'f5', 'f6')):
            o = 16 * i + 4 * k
            a.emit('lwc1', 'f0', o, 't2'); a.emit('sub.s', 'f0', 'f0', fs)
            a.emit('mul.s', 'f0', 'f0', 'f12'); a.emit('add.s', 'f0', 'f0', fs)
            a.emit('swc1', 'f0', o, 't2')
    a.emit('j', 0x27590C); a.emit('nop')
    return a
def patches():
    return [(WIDE + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x5B699C, 0x08000000 | (WIDE >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
