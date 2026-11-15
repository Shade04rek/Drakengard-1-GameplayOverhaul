import sys, struct
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
BOOST = 0x5B7800
T, PREVP, PREVL = 0x78F0, 0x78F4, 0x78F8      # words at 005B78F0.. (lui t0,0x5B)
FRAMES = 60                                   # fade time (1 s)
AMOUNT = 0.25                                 # +25 % at the start
def fbits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def li_f(a, freg, x):
    b = fbits(x); a.emit('lui', 't1', b >> 16)
    if b & 0xFFFF: a.emit('ori', 't1', 't1', b & 0xFFFF)
    a.emit('mtc1', 't1', freg)
def build():
    a = Asm(BOOST)
    a.emit('mul.s', 'f20', 'f26', 'f1')       # run speed * m (what cave 2 did)
    a.emit('lui', 't0', 0x5B)
    a.emit('lui', 't1', 0x57)
    a.emit('lbu', 'v0', -0x327E, 't1')        # pad byte 0056CD82, L3 = bit 1, active low
    a.emit('andi', 'v0', 'v0', 2)
    a.emit('xori', 'v0', 'v0', 2)             # 2 = L3 held now
    a.emit('lw', 'v1', PREVP, 't0'); a.emit('sw', 'v0', PREVP, 't0')
    a.emit('lui', 't1', 0x2F)
    a.emit('lw', 'a0', 0x345C, 't1')          # sprint latch
    a.emit('lw', 'a1', PREVL, 't0'); a.emit('sw', 'a0', PREVL, 't0')
    a.emit('lw', 'a2', T, 't0')
    a.emit('beq', 'a0', 'zero', 'OFF'); a.emit('nop')
    a.emit('beq', 'v0', 'zero', 'NOE'); a.emit('nop')     # L3 not held
    a.emit('bne', 'v1', 'zero', 'NOE'); a.emit('nop')     # held last frame too: not a new press
    a.emit('beq', 'a1', 'zero', 'NOE'); a.emit('nop')     # was not sprinting yet: this press starts the sprint
    a.emit('addiu', 'a2', 'zero', FRAMES)
    # wind burst, as the super sprint start does it (SSC): restart the burst slot and drop the walk timer below
    # 0x4000 so the sprint hook sends it through the 0x3FFF step next frame and the game plays the burst
    a.emit('addiu', 'v0', 'zero', 0x3000); a.emit('sw', 'v0', 0x6A0, 's2')
    a.emit('addiu', 'v0', 'zero', 0xEE); a.emit('sw', 'v0', 0x560, 's2')
    a.emit('sw', 'zero', 0x564, 's2')
    a.label('NOE')
    a.emit('beq', 'a2', 'zero', 'STORE'); a.emit('nop')
    a.emit('mtc1', 'a2', 'f0'); a.emit('cvt.s.w', 'f0', 'f0')
    li_f(a, 'f2', AMOUNT / FRAMES); a.emit('mul.s', 'f0', 'f0', 'f2')
    li_f(a, 'f2', 1.0); a.emit('add.s', 'f0', 'f0', 'f2')
    a.emit('mul.s', 'f20', 'f20', 'f0')       # speed * (1 + 0.25 * frames left / 60)
    a.emit('beq', 'zero', 'zero', 'STORE')
    a.emit('addiu', 'a2', 'a2', -1)
    a.label('OFF')
    a.emit('or', 'a2', 'zero', 'zero')
    a.label('STORE')
    a.emit('sw', 'a2', T, 't0')
    a.emit('j', 0x170204)
    a.emit('lh', 'v0', 0x18, 's4')            # what cave 2 ran in its delay slot
    return a
if __name__ == '__main__':
    a = build()
    for i, w in enumerate(a.assemble()): print('patch=1,EE,%08X,word,%08X' % (BOOST + 4 * i, w))
    print('patch=1,EE,0031B678,word,%08X' % (0x08000000 | (BOOST >> 2)))
