import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
CF = 0x5B7D00
def fbits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fbits(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def build():
    a = Asm(CF)
    a.emit('lui', 't0', 0x32); a.emit('lw', 't0', 0x1E2C, 't0'); a.emit('andi', 't0', 't0', 1)
    a.emit('bne', 't0', 'zero', 'RET'); a.emit('nop')                 # lock-on: FACE turns him to the target
    a.emit('lw', 'a0', 0x34, 'sp')                                    # Caim (W saved a0)
    a.emit('lw', 't1', 0x2D0, 'a0'); a.emit('xori', 't1', 't1', 2); a.emit('bne', 't1', 'zero', 'RET'); a.emit('nop')
    a.emit('lw', 't1', 0x2DC, 'a0'); a.emit('xori', 't1', 't1', 4); a.emit('bne', 't1', 'zero', 'RET'); a.emit('nop')
    a.emit('lh', 't0', 0x67C, 'a0'); a.emit('lh', 't1', 0x67E, 'a0') # stick x, y in Caim's frame (forward = -y)
    a.emit('sra', 't3', 't0', 31); a.emit('xor', 't4', 't0', 't3'); a.emit('subu', 't4', 't4', 't3')
    a.emit('sra', 't3', 't1', 31); a.emit('xor', 't5', 't1', 't3'); a.emit('subu', 't5', 't5', 't3')
    a.emit('addu', 't4', 't4', 't5'); a.emit('slti', 't4', 't4', 0x400)
    a.emit('bne', 't4', 'zero', 'RET'); a.emit('nop')                 # dead zone
    # delta = atan2(x, -y) (polynomial atan, as in TURNC / FACE)
    a.emit('mtc1', 't0', 'f1'); a.emit('cvt.s.w', 'f1', 'f1')
    a.emit('subu', 't1', 'zero', 't1'); a.emit('mtc1', 't1', 'f2'); a.emit('cvt.s.w', 'f2', 'f2')
    a.emit('abs.s', 'f3', 'f1'); a.emit('abs.s', 'f4', 'f2')
    a.emit('daddu', 't2', 'zero', 'zero')
    a.emit('c.olt.s', 'f4', 'f3'); a.emit('bc1f', 'D1'); a.emit('nop')
    a.emit('div.s', 'f5', 'f4', 'f3'); a.emit('ori', 't2', 'zero', 1)
    a.emit('beq', 'zero', 'zero', 'D2'); a.emit('nop')
    a.label('D1'); a.emit('div.s', 'f5', 'f3', 'f4')
    a.label('D2')
    a.emit('mul.s', 'f6', 'f5', 'f5')
    lif(a, 'f7', 0.0208351); 
    for c in (-0.085133, 0.180141, -0.3302995, 0.999866):
        a.emit('mul.s', 'f7', 'f7', 'f6'); lif(a, 'f8', c); a.emit('add.s', 'f7', 'f7', 'f8')
    a.emit('mul.s', 'f7', 'f7', 'f5')                                 # atan(min/max)
    a.emit('beq', 't2', 'zero', 'D3'); a.emit('nop')
    lif(a, 'f8', math.pi / 2); a.emit('sub.s', 'f7', 'f8', 'f7')
    a.label('D3')
    a.emit('mtc1', 'zero', 'f8')
    a.emit('c.olt.s', 'f2', 'f8'); a.emit('bc1f', 'D4'); a.emit('nop')
    lif(a, 'f8', math.pi); a.emit('sub.s', 'f7', 'f8', 'f7')
    a.label('D4')
    a.emit('mtc1', 'zero', 'f8')
    a.emit('c.olt.s', 'f1', 'f8'); a.emit('bc1f', 'D5'); a.emit('nop')
    a.emit('neg.s', 'f7', 'f7')
    a.label('D5')
    # turn like FACE: yaw-delta accumulator, chase yaw, flags
    a.emit('lwc1', 'f9', 0x44, 'a0'); a.emit('add.s', 'f9', 'f9', 'f7')
    lif(a, 'f10', math.pi); lif(a, 'f11', 2 * math.pi); a.emit('neg.s', 'f12', 'f10')
    a.emit('c.olt.s', 'f10', 'f9'); a.emit('bc1f', 'W1'); a.emit('nop'); a.emit('sub.s', 'f9', 'f9', 'f11')
    a.label('W1')
    a.emit('c.olt.s', 'f9', 'f12'); a.emit('bc1f', 'W2'); a.emit('nop'); a.emit('add.s', 'f9', 'f9', 'f11')
    a.label('W2')
    a.emit('swc1', 'f9', 0x584, 'a0')
    a.emit('swc1', 'f7', 0x204, 'a0')
    a.emit('lw', 't6', 0x210, 'a0'); a.emit('ori', 't6', 't6', 2); a.emit('sw', 't6', 0x210, 'a0')
    a.emit('lw', 't6', 0x570, 'a0'); a.emit('ori', 't6', 't6', 1); a.emit('sw', 't6', 0x570, 'a0')
    a.label('RET')
    a.emit('lw', 'v0', 0x38, 'sp')                                    # W's return (ra was restored in the hook's delay slot)
    a.emit('jr', 'ra')
    a.emit('addiu', 'sp', 'sp', 0x40)
    return a
if __name__ == '__main__':
    a = build()
    for i, w in enumerate(a.assemble()): print('patch=1,EE,%08X,word,%08X' % (CF + 4 * i, w))
    print('patch=1,EE,00342098,word,%08X' % (0x08000000 | (CF >> 2)))
