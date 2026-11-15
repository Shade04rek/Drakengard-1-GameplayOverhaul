import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
BSK = 0x5BC500
# Block special for every weapon. RS stage 2 -> 3 (00321C0C..00321C34) injects the spell press while the first attack
# runs; the attack state FUN_0017C14C turns a spell press into the weapon special only when the combo entry after the
# current one (FUN_0016E288(+0x6D0 + 2), byte 9 of the weapon combo entry) is non-zero, which for Caim's sword is the
# first hit but for other weapons a later one. 00321C34 (ori t3,zero,3) becomes j BSK (NOT jal: RS ends in jr ra back to the game, so ra must survive; the sw t3
# behind it runs in the delay slot; BSK saves / restores ra around its calls and returns with j 00321C3C); BSK finds the first entry k = 2, 4, ... (< 0x40) with FUN_0016E288(k) != 0 and sets +0x6D0 = k - 2,
# so the game sees the spell press at the point of the combo where this weapon has its special; no entry = unchanged.
# Then it does the replaced stage = 3 store itself (t3 = 3 -> 00321E38) and returns with t8 = 0x320000, a0 = Caim.
def build():
    a = Asm(BSK)
    a.emit('addiu', 'sp', 'sp', -0x20)
    a.emit('sw', 'ra', 0, 'sp'); a.emit('sw', 'a0', 4, 'sp'); a.emit('sw', 's1', 8, 'sp')
    a.emit('ori', 's1', 'zero', 2)
    a.label('LOOP')
    a.emit('jal', 0x16E288); a.emit('daddu', 'a0', 's1', 'zero')
    a.emit('bne', 'v0', 'zero', 'FOUND'); a.emit('nop')
    a.emit('addiu', 's1', 's1', 2)
    a.emit('sltiu', 'v0', 's1', 0x40); a.emit('bne', 'v0', 'zero', 'LOOP'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'DONE'); a.emit('nop')
    a.label('FOUND')
    a.emit('lw', 'a0', 4, 'sp'); a.emit('addiu', 'v0', 's1', -2); a.emit('sw', 'v0', 0x6D0, 'a0')
    a.label('DONE')
    a.emit('lw', 'ra', 0, 'sp'); a.emit('lw', 'a0', 4, 'sp'); a.emit('lw', 's1', 8, 'sp')
    a.emit('addiu', 'sp', 'sp', 0x20)
    a.emit('lui', 't8', 0x32); a.emit('ori', 't3', 'zero', 3)
    a.emit('j', 0x321C3C); a.emit('sw', 't3', 0x1E38, 't8')
    return a
def patches():
    return [(BSK + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x321C34, 0x08000000 | (BSK >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
