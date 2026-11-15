import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
SW = 0x5B7F10
SPELL = 0x17D954                    # ground spell state (sub-mode 6), called at 0017382C
FACE = 0x341E00                     # lock-on facing routine (a0 = Caim)
TURN_RATE = 0.07                    # rad per frame at full stick left / right (stick +-4096)
def fbits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fbits(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def build():
    a = Asm(SW)
    a.emit('addiu', 'sp', 'sp', -0x20)
    a.emit('sw', 'ra', 0x10, 'sp'); a.emit('sw', 'a0', 0x14, 'sp')
    a.emit('jal', SPELL); a.emit('nop')
    a.emit('sw', 'v0', 0x18, 'sp')
    a.emit('lw', 'a0', 0x14, 'sp')
    a.emit('lw', 't1', 0x2DC, 'a0'); a.emit('xori', 't1', 't1', 6)
    a.emit('bne', 't1', 'zero', 'RET'); a.emit('nop')                 # still casting (sub-mode 6)
    a.emit('lui', 't0', 0x32); a.emit('lw', 't0', 0x1E2C, 't0'); a.emit('andi', 't0', 't0', 1)
    a.emit('beq', 't0', 'zero', 'STICK'); a.emit('nop')
    a.emit('jal', FACE); a.emit('nop')                                # lock-on: face the target (a0 = Caim)
    a.emit('beq', 'zero', 'zero', 'RET'); a.emit('nop')
    a.label('STICK')
    a.emit('lh', 't0', 0x67C, 'a0')                                   # stick x in Caim's frame (+ = right)
    a.emit('addiu', 't1', 't0', 0x400); a.emit('sltiu', 't1', 't1', 0x801)
    a.emit('bne', 't1', 'zero', 'RET'); a.emit('nop')                 # dead zone
    a.emit('mtc1', 't0', 'f1'); a.emit('cvt.s.w', 'f1', 'f1')
    lif(a, 'f2', TURN_RATE / 4096.0); a.emit('mul.s', 'f7', 'f1', 'f2')   # yaw step
    a.emit('lwc1', 'f9', 0x44, 'a0'); a.emit('add.s', 'f9', 'f9', 'f7')
    lif(a, 'f10', math.pi); lif(a, 'f11', 2 * math.pi); a.emit('neg.s', 'f12', 'f10')
    a.emit('c.olt.s', 'f10', 'f9'); a.emit('bc1f', 'W1'); a.emit('nop'); a.emit('sub.s', 'f9', 'f9', 'f11')
    a.label('W1')
    a.emit('c.olt.s', 'f9', 'f12'); a.emit('bc1f', 'W2'); a.emit('nop'); a.emit('add.s', 'f9', 'f9', 'f11')
    a.label('W2')
    a.emit('swc1', 'f9', 0x584, 'a0'); a.emit('swc1', 'f7', 0x204, 'a0')
    a.emit('lw', 't6', 0x210, 'a0'); a.emit('ori', 't6', 't6', 2); a.emit('sw', 't6', 0x210, 'a0')
    a.emit('lw', 't6', 0x570, 'a0'); a.emit('ori', 't6', 't6', 1); a.emit('sw', 't6', 0x570, 'a0')
    a.label('RET')
    a.emit('lw', 'v0', 0x18, 'sp'); a.emit('lw', 'ra', 0x10, 'sp')
    a.emit('jr', 'ra'); a.emit('addiu', 'sp', 'sp', 0x20)
    return a
JW = 0x5B8230
JUMP = 0x174FC0                     # jump state (sub-mode 5), called at 0017381C
def build_jw():
    a = Asm(JW)
    a.emit('addiu', 'sp', 'sp', -0x20)
    a.emit('sw', 'ra', 0x10, 'sp'); a.emit('sw', 'a0', 0x14, 'sp')
    a.emit('jal', JUMP); a.emit('nop')
    a.emit('sw', 'v0', 0x18, 'sp')
    a.emit('lui', 't0', 0x32); a.emit('lw', 't0', 0x1E2C, 't0'); a.emit('andi', 't0', 't0', 1)
    a.emit('beq', 't0', 'zero', 'JRET'); a.emit('nop')               # lock-on only
    a.emit('lw', 'a0', 0x14, 'sp')
    a.emit('lw', 't1', 0x2DC, 'a0'); a.emit('xori', 't1', 't1', 5)
    a.emit('bne', 't1', 'zero', 'JRET'); a.emit('nop')               # still in the jump state
    a.emit('lw', 't1', 0x660, 'a0')
    a.emit('beq', 't1', 'zero', 'JRET'); a.emit('nop')               # a jump attack is running (type != 0)
    a.emit('jal', FACE); a.emit('nop')
    a.label('JRET')
    a.emit('lw', 'v0', 0x18, 'sp'); a.emit('lw', 'ra', 0x10, 'sp')
    a.emit('jr', 'ra'); a.emit('addiu', 'sp', 'sp', 0x20)
    return a
if __name__ == '__main__':
    a = build()
    for i, w in enumerate(a.assemble()): print('patch=1,EE,%08X,word,%08X' % (SW + 4 * i, w))
    print('patch=1,EE,0017382C,word,%08X' % (0x0C000000 | (SW >> 2)))
    j = build_jw()
    for i, w in enumerate(j.assemble()): print('patch=1,EE,%08X,word,%08X' % (JW + 4 * i, w))
    print('patch=1,EE,0017381C,word,%08X' % (0x0C000000 | (JW >> 2)))
