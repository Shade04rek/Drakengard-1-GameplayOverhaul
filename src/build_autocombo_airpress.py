"""Hold the attack action to auto-attack (the ground combo repeats): Caim and the allies Leonard 0x6A / Seere 0x6B / Arioch 0x6C
(word 003ACF00). The attack action's button is found through the game's own mapping table (byte 005747B6 = button index, 0x0F = R2
by default; pressure byte = 00342864 + index), so the in-game mapping decides which button it is. While it is held the press is
mashed: 8 frames held, 8 frames released. Aerial stages (marker 00340DFC != 0) are untouched. Runs in the pad-update chain
(T2 -> hook 00321A74), then continues into SQ."""
AUTO = 0x5BD700
HOOK = 0x321A74
SQ = 0x5BBE00
CNT = -0x4014            # 005BBFEC (lui 0x5C): frame counter
HELD = -0x400C           # 005BBFF4 (lui 0x5C): frames the attack action has been held in the air
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
def build():
    a = Asm(AUTO)
    a.emit('lui', 't0', 0x32); a.emit('lw', 't0', 0x1E30, 't0')            # levels marker
    a.emit('beq', 't0', 'zero', 'GO'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't0', 0xDFC, 't0'); a.emit('bne', 't0', 'zero', 'GO'); a.emit('nop')     # aerial stage: untouched
    a.emit('lui', 't1', 0x57); a.emit('lbu', 't1', 0x47B6, 't1')           # attack action's button index
    a.emit('lui', 't7', 0x34); a.emit('addu', 't7', 't7', 't1')
    a.emit('lbu', 't0', 0x2864, 't7')                                      # its pressure
    a.emit('sltiu', 't0', 't0', 0x40); a.emit('beq', 't0', 'zero', 'HLD'); a.emit('nop')
    a.emit('lui', 't9', 0x5C); a.emit('sw', 'zero', HELD, 't9'); a.emit('beq', 'zero', 'zero', 'GO'); a.emit('nop')
    a.label('HLD')
    # airborne (Caim +0x2DC == 5, the jump state = air slashes): one press = one attack; the press is passed for 4 frames and cut until released
    a.emit('lui', 't9', 0x5C)
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't0', -0x3744, 't0'); a.emit('addiu', 't0', 't0', -5); a.emit('bne', 't0', 'zero', 'MASH'); a.emit('nop')
    a.emit('lw', 't0', HELD, 't9'); a.emit('addiu', 't0', 't0', 1); a.emit('sw', 't0', HELD, 't9')
    a.emit('sltiu', 't0', 't0', 5); a.emit('bne', 't0', 'zero', 'GO'); a.emit('nop')
    a.emit('sb', 'zero', 0x2864, 't7'); a.emit('beq', 'zero', 'zero', 'GO'); a.emit('nop')
    a.label('MASH')
    a.emit('lw', 't0', CNT, 't9'); a.emit('addiu', 't0', 't0', 1); a.emit('sw', 't0', CNT, 't9')
    a.emit('andi', 't0', 't0', 8); a.emit('bne', 't0', 'zero', 'GO'); a.emit('nop')
    a.emit('sb', 'zero', 0x2864, 't7')                                     # released phase
    a.label('GO')
    a.emit('j', SQ); a.emit('nop')
    return a
def patches():
    return [(AUTO + 4 * i, w) for i, w in enumerate(build().assemble())] + [(HOOK, 0x08000000 | (AUTO >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))


