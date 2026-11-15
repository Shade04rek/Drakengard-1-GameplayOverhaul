"""Sprint after a ground combo and sprint through the air slashes.
AUTOC2 (hook 001701BC, replaces AUTOC 00321F70 of the sprint-resume section): in the first walk frames after a ground combo in which L3 was held
(PEND, word 005BE1F8: 0xFF set by the Auto-attack cave AUTO during the combo) a 20 frame window starts; in each walk frame of it the stick
(Caim shorts +0x67C x / +0x67E y, +-0x1000 full) at 0xE00 or more from the centre in ANY direction presses L3 for the walk code (v1 = 0, the
latch / wind burst / sprint speed then start as for a real press). Without it the old AUTOC logic runs (flag 0033EDFC + stick forward).
SPC (005BE340, hook 005B7C18 in the air dash section's PRE cave: j SPC, 005B7C1C nop): after the 2nd R2 slash (0033F6DC != 0) a sprinting Caim
(latch 002F345C) is not slowed: the halving block is skipped, the resume flag 0033EDFC is set (landing keeps the sprint with the stick forward)
and the super sprint count 005B1F00 restarts (the 5 seconds start again)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
AUTOC2 = 0x5BE280
SPC = 0x5BE340
PEND = -0x1E08          # 005BE1F8 (lui 0x5C)
WINDOW = 21             # frames + 1
FULL2 = 0xC4            # lui: (0xC4 << 16) = 12845056 = 3584^2
RET = 0x1701C4          # where the old AUTOC jumped
HREF = 0x7CFC
TOAD = 0x5B7CC8
HALF_AFTER = 0x5B7C20   # bne t1,zero,HON (after the replaced lui t2 / lw t1)
def build_autoc2():
    a = Asm(AUTOC2)
    a.emit('andi', 'v1', 'v1', 2)                                  # replaced instruction
    a.emit('lui', 'a2', 0x5C); a.emit('lw', 'a3', PEND, 'a2')
    a.emit('beq', 'a3', 'zero', 'OLD'); a.emit('nop')
    a.emit('xori', 'at', 'a3', 0xFF); a.emit('bne', 'at', 'zero', 'HAVE'); a.emit('nop')
    a.emit('ori', 'a3', 'zero', WINDOW)                            # first walk frame after the combo
    a.label('HAVE')
    a.emit('addiu', 'a3', 'a3', -1); a.emit('sw', 'a3', PEND, 'a2')
    a.emit('lh', 'a3', 0x67C, 's2'); a.emit('mult', 'a3', 'a3'); a.emit('mflo', 'a3')
    a.emit('lh', 'at', 0x67E, 's2'); a.emit('mult', 'at', 'at'); a.emit('mflo', 'at')
    a.emit('addu', 'a3', 'a3', 'at')
    a.emit('lui', 'at', FULL2); a.emit('sltu', 'a3', 'a3', 'at'); a.emit('bne', 'a3', 'zero', 'OLD'); a.emit('nop')   # not at full tilt
    a.emit('sw', 'zero', PEND, 'a2')
    a.emit('beq', 'zero', 'zero', 'PRESS'); a.emit('nop')
    a.label('OLD')
    a.emit('lui', 'a2', 0x34); a.emit('lw', 'a3', -0x1204, 'a2'); a.emit('beq', 'a3', 'zero', 'DONE'); a.emit('sw', 'zero', -0x1204, 'a2')
    a.emit('lh', 'a3', 0x67E, 's2'); a.emit('slti', 'a3', 'a3', -0x800); a.emit('beq', 'a3', 'zero', 'DONE'); a.emit('nop')
    a.label('PRESS')
    a.emit('daddu', 'v1', 'zero', 'zero')
    a.label('DONE')
    a.emit('j', RET); a.emit('nop')
    return a
def build_spc():
    a = Asm(SPC)
    a.emit('lui', 't2', 0x34); a.emit('lw', 't1', -0x924, 't2')    # the replaced pair: 0033F6DC
    a.emit('beq', 't1', 'zero', 'BACK'); a.emit('nop')
    a.emit('lui', 't3', 0x2F); a.emit('lw', 't3', 0x345C, 't3')    # sprint latch
    a.emit('beq', 't3', 'zero', 'BACK'); a.emit('nop')
    a.emit('ori', 't3', 'zero', 1); a.emit('sw', 't3', -0x1204, 't2')   # landing with the stick forward resumes the sprint
    a.emit('lui', 't3', 0x5B); a.emit('sw', 'zero', 0x1F00, 't3'); a.emit('sw', 'zero', HREF, 't3')   # super sprint count restarts
    a.emit('j', TOAD); a.emit('nop')
    a.label('BACK')
    a.emit('j', HALF_AFTER); a.emit('nop')
    return a
NOSA = 0x5BE3A0
def build_nosa():
    # hook 00173CD8 (lw v0,0x6A0(s0) ; sltiu v0,v0,0x4000 of the attack start FUN_00173C84: timer >= 0x4000 = sprint attack): with the flag word 005BE1FC
    # (set by AUTO while the attack action is held in the air, cleared when released) the first ground attack is a normal combo attack (v0 = 1)
    a = Asm(NOSA)
    a.emit('lw', 'v0', 0x6A0, 's0'); a.emit('sltiu', 'v0', 'v0', 0x4000)
    # the R2-after-block section hooks the same word: its flag word 005B1F60 forces the sprint attack (v0 = 0), kept here (this hook is written later and wins)
    a.emit('lui', 't0', 0x5B); a.emit('lw', 't1', 0x1F60, 't0'); a.emit('beq', 't1', 'zero', 'CK'); a.emit('nop')
    a.emit('daddu', 'v0', 'zero', 'zero'); a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('CK')
    a.emit('lui', 't0', 0x5C); a.emit('lw', 't1', -0x1E04, 't0'); a.emit('beq', 't1', 'zero', 'OUT'); a.emit('nop')
    a.emit('ori', 'v0', 'zero', 1); a.emit('sw', 'zero', -0x1E04, 't0')
    a.label('OUT')
    a.emit('j', 0x173CE0); a.emit('nop')
    return a
BH2 = 0x5BE420
DFC = 0x5BE460
NOSJC = 0x5BE4A0
def build_bh2():
    # hook 00321CA0 (j 00179954 at the end of BH, the block special's cave, a0 / a1 = the guard call's arguments): DFB (005BE1F4) = 2 was written by
    # the spell / arrow deflect just before it entered the guard path -> 1 = this block comes from a deflect; any other call clears it
    a = Asm(BH2)
    a.emit('lui', 't3', 0x5C); a.emit('lw', 't4', -0x1E0C, 't3'); a.emit('xori', 't6', 't4', 2); a.emit('bne', 't6', 'zero', 'REAL'); a.emit('nop')
    a.emit('ori', 't4', 'zero', 1); a.emit('sw', 't4', -0x1E0C, 't3'); a.emit('j', 0x179954); a.emit('nop')
    a.label('REAL')
    a.emit('sw', 'zero', -0x1E0C, 't3'); a.emit('j', 0x179954); a.emit('nop')
    return a
def build_dfc():
    # hook 005B2430 / 005B2434 in the R2-after-block cave SPR (andi t7,t1,8 ; beq t7,zero,005B245C): with DFB == 1 the attack press does not start the
    # R2 counterattack (only the R1 special works after a deflect block)
    a = Asm(DFC)
    a.emit('andi', 't7', 't1', 8); a.emit('beq', 't7', 'zero', 'NO'); a.emit('nop')
    a.emit('lui', 't3', 0x5C); a.emit('lw', 't3', -0x1E0C, 't3'); a.emit('xori', 't3', 't3', 1); a.emit('beq', 't3', 'zero', 'NO'); a.emit('nop')
    a.emit('j', 0x5B243C); a.emit('nop')
    a.label('NO')
    a.emit('j', 0x5B245C); a.emit('nop')
    return a
def build_nosjc():
    # hook 001751DC / 001751E0 (jump takeoff in FUN_00174FC0: walk timer >= 0x4000 = sprint jump slash): NOSJ (005BE1F0, set by AUTO while the attack
    # action is held in / after a ground combo, cleared on release) makes it a normal jump slash and ends the sprint (latch 002F345C, multiplier
    # 002F340C = 1.0, super sprint count 005B1F00)
    a = Asm(NOSJC)
    a.emit('lw', 'v0', 0x6A0, 's1'); a.emit('sltiu', 'v0', 'v0', 0x4000)
    a.emit('lui', 't0', 0x5C); a.emit('lw', 't1', -0x1E10, 't0'); a.emit('beq', 't1', 'zero', 'OUT'); a.emit('nop')
    a.emit('ori', 'v0', 'zero', 1)
    a.emit('lui', 't0', 0x2F); a.emit('sw', 'zero', 0x345C, 't0'); a.emit('lui', 't1', 0x3F80); a.emit('sw', 't1', 0x340C, 't0')
    a.emit('lui', 't0', 0x5B); a.emit('sw', 'zero', 0x1F00, 't0')
    a.label('OUT')
    a.emit('j', 0x1751E4); a.emit('nop')
    return a
def patches():
    p = [(AUTOC2 + 4 * i, w) for i, w in enumerate(build_autoc2().assemble())]
    p += [(SPC + 4 * i, w) for i, w in enumerate(build_spc().assemble())]
    p += [(NOSA + 4 * i, w) for i, w in enumerate(build_nosa().assemble())]
    p += [(0x173CD8, 0x08000000 | (NOSA >> 2)), (0x173CDC, 0)]
    for base, b in ((BH2, build_bh2()), (DFC, build_dfc()), (NOSJC, build_nosjc())): p += [(base + 4 * i, w) for i, w in enumerate(b.assemble())]
    p += [(0x321CA0, 0x08000000 | (BH2 >> 2)), (0x5B2430, 0x08000000 | (DFC >> 2)), (0x5B2434, 0), (0x1751DC, 0x08000000 | (NOSJC >> 2)), (0x1751E0, 0)]
    p += [(0x1701BC, 0x08000000 | (AUTOC2 >> 2)), (0x5B7C18, 0x08000000 | (SPC >> 2)), (0x5B7C1C, 0)]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
