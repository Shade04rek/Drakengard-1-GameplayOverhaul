"""Regular double jump: pressing the jump button again in the air does a plain second jump (no attack), once per jump.
Hook: DJ2 (the slash / R1 double jump cave, section 'slash jump double jump') at 00342C10 (beq v1,zero,00342C20; v1 = [Caim+0x2EC], 0 = takeoff).
Its delay-slot partner 00342C14 (or t8,t1,t2) still runs. JD: v1 == 0 -> clear the used flag and go on at 00342C20; airborne -> on a new
press of the jump button (held word [Caim+0x66C] bit 0x200, own edge memory) with the flag unused: set the flag, [Caim+0x2EC] = 0
(the game runs the takeoff again, the way the R1 double jump does) and continue at 00174FE4 with v1 = 0; otherwise go on at 00342C88.
Only at / k0 / k1 are used (DJ2 needs t0-t9)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
JD = 0x5BDF40
PREV, USED = -0x20F0, -0x20EC        # 005BDF10 / 005BDF14 (lui 0x5C)
def build():
    a = Asm(JD)
    a.emit('lui', 'k0', 0x5C)
    a.emit('bne', 'v1', 'zero', 'AIR'); a.emit('nop')
    a.emit('sw', 'zero', USED, 'k0'); a.emit('ori', 'at', 'zero', 1); a.emit('sw', 'at', PREV, 'k0')      # the takeoff press counts as held
    a.emit('j', 0x342C20); a.emit('nop')
    a.label('AIR')
    a.emit('lw', 'k1', 0x66C, 's1'); a.emit('andi', 'k1', 'k1', 0x200)
    a.emit('lw', 'at', PREV, 'k0'); a.emit('sw', 'k1', PREV, 'k0')
    a.emit('beq', 'k1', 'zero', 'OUT'); a.emit('nop')
    a.emit('bne', 'at', 'zero', 'OUT'); a.emit('nop')
    a.emit('lw', 'at', USED, 'k0'); a.emit('bne', 'at', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 'k1', 0x14); a.emit('lw', 'at', -6864, 'k1'); a.emit('bne', 'at', 'zero', 'OUT'); a.emit('nop')     # the R1 double jump was used
    a.emit('lui', 'k1', 0x34); a.emit('lw', 'at', -0x924, 'k1'); a.emit('bne', 'at', 'zero', 'OUT'); a.emit('nop')    # the slash double jump chain was used
    a.emit('ori', 'at', 'zero', 1); a.emit('sw', 'at', USED, 'k0')
    a.emit('sw', 'zero', 0x2EC, 's1')
    a.emit('j', 0x174FE4); a.emit('daddu', 'v1', 'zero', 'zero')
    a.label('OUT')
    a.emit('j', 0x342C88); a.emit('nop')
    return a
def patches():
    return [(JD + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x342C10, 0x08000000 | (JD >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))

