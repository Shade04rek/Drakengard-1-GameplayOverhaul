"""Hold the attack action to auto-attack (the ground combo repeats): Caim and the allies. The attack action's button is found
through the game's own mapping table (byte 005747B6 = button index, 0x0F = R2 by default; pressure byte = 00342864 + index), so
the in-game mapping decides which button it is. A press always passes through at once (the first 8 frames of a hold); only if it
stays held is it then cut for 8 frames and passed for 8, and so on, so a tap is never eaten. Aerial stages (marker 00340DFC != 0)
are untouched. Runs in the pad-update chain (T2 -> hook 00321A74), then continues into SQ."""
AUTO = 0x5BD700
HOOK = 0x321A74
SQ = 0x5BBE00
AIR_PASS, AIR_PERIOD, AIR_SECOND = 5, 10, 12   # air slashes: frames passed / cycle length / hold frame of the 2nd slash
HELD = -0x4014           # 005BBFEC (lui 0x5C): frames the attack action has been held
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
def build():
    a = Asm(AUTO)
    a.emit('lui', 't0', 0x32); a.emit('lw', 't0', 0x1E30, 't0')            # levels marker
    a.emit('beq', 't0', 'zero', 'GO'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't0', 0xDFC, 't0'); a.emit('bne', 't0', 'zero', 'GO'); a.emit('nop')
    # sprint buffered during a ground combo (Caim main state [+0x2D0] 2, sub state [+0x2DC] 4): L3 held -> PEND (word 005BE1F8) = 0xFF; the pad's
    # L3 is read as in the walk cave (byte 0056CD82 bit 1, active low); a combo without L3 clears an old value. AUTOC2 (sprint resume
    # section) uses it in the first walk frames after the combo. Uses t3, t4, t6 only.
    a.emit('lui', 't3', 0x3B); a.emit('lw', 't4', -0x3750, 't3'); a.emit('xori', 't4', 't4', 2); a.emit('bne', 't4', 'zero', 'PQN'); a.emit('nop')
    a.emit('lw', 't4', -0x3744, 't3'); a.emit('xori', 't4', 't4', 4); a.emit('bne', 't4', 'zero', 'PQN'); a.emit('nop')
    a.emit('lui', 't6', 0x57); a.emit('lbu', 't4', -0x327E, 't6'); a.emit('andi', 't4', 't4', 2)
    a.emit('lui', 't3', 0x5C)
    a.emit('beq', 't4', 'zero', 'PQS'); a.emit('nop')                      # bit clear = pressed
    a.emit('lw', 't6', -0x1E08, 't3'); a.emit('xori', 't6', 't6', 0xFF); a.emit('beq', 't6', 'zero', 'PQN'); a.emit('nop')
    a.emit('sw', 'zero', -0x1E08, 't3'); a.emit('beq', 'zero', 'zero', 'PQN'); a.emit('nop')
    a.label('PQS')
    a.emit('ori', 't6', 'zero', 0xFF); a.emit('sw', 't6', -0x1E08, 't3')
    a.label('PQN')
    a.emit('lui', 't1', 0x57); a.emit('lbu', 't1', 0x47B6, 't1')           # attack action's button index
    a.emit('lui', 't7', 0x34); a.emit('addu', 't7', 't7', 't1')
    a.emit('lui', 't9', 0x5C)
    a.emit('lbu', 't0', 0x2864, 't7')                                      # its pressure
    a.emit('sltiu', 't0', 't0', 0x40); a.emit('beq', 't0', 'zero', 'DN'); a.emit('nop')
    a.emit('lui', 't3', 0x5C); a.emit('sw', 'zero', -0x1E04, 't3')                       # NOSA (005BE1FC): released = no block of the sprint attack
    a.emit('sw', 'zero', -0x1E10, 't3')                                                 # NOSJ (005BE1F0): released = sprint jump attacks allowed again
    a.emit('sw', 'zero', HELD, 't9'); a.emit('beq', 'zero', 'zero', 'GO'); a.emit('nop')    # not held: counter reset
    a.label('DN')
    a.emit('lw', 't0', HELD, 't9'); a.emit('addiu', 't0', 't0', 1); a.emit('sw', 't0', HELD, 't9')
    a.emit('lui', 't3', 0x3B); a.emit('lw', 't4', -0x3744, 't3'); a.emit('xori', 't4', 't4', 4); a.emit('bne', 't4', 'zero', 'NJS'); a.emit('nop')   # held in a ground combo (sub state 4): NOSJ
    a.emit('lui', 't3', 0x5C); a.emit('ori', 't4', 'zero', 1); a.emit('sw', 't4', -0x1E10, 't3')
    a.label('NJS')
    # airborne (Caim +0x2DC == 5, the jump state = the air slashes): the 2nd slash starts at hold frame AIR_SECOND (ground: 16); from
    # the second slash on the cycle is 20 frames (8 passed, 12 cut), so the 2nd to 3rd slash gap is a little longer
    a.emit('lui', 't1', 0x3B); a.emit('lw', 't1', -0x3744, 't1'); a.emit('addiu', 't1', 't1', -5); a.emit('bne', 't1', 'zero', 'GRD'); a.emit('nop')
    a.emit('lui', 't3', 0x5C); a.emit('ori', 't4', 'zero', 1); a.emit('sw', 't4', -0x1E04, 't3')   # NOSA: attack held in the air -> the first ground attack is no sprint attack
    a.emit('sltiu', 't1', 't0', 8); a.emit('bne', 't1', 'zero', 'GO'); a.emit('nop')                 # 1st slash: always passes
    a.emit('sltiu', 't1', 't0', AIR_SECOND); a.emit('bne', 't1', 'zero', 'CUT'); a.emit('nop')       # gap to the 2nd slash
    a.emit('sltiu', 't1', 't0', AIR_SECOND + AIR_PERIOD); a.emit('bne', 't1', 'zero', 'AK'); a.emit('nop')
    a.emit('ori', 't0', 'zero', AIR_SECOND); a.emit('sw', 't0', HELD, 't9')
    a.label('AK')
    a.emit('sltiu', 't0', 't0', AIR_SECOND + AIR_PASS); a.emit('bne', 't0', 'zero', 'GO'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'CUT'); a.emit('nop')
    a.label('GRD')
    a.emit('andi', 't0', 't0', 8)                                          # frames 1..8 pass, 9..16 cut, 17..24 pass ...
    a.emit('beq', 't0', 'zero', 'GO'); a.emit('nop')
    a.label('CUT')
    a.emit('sb', 'zero', 0x2864, 't7')
    a.label('GO')
    a.emit('j', SQ); a.emit('nop')
    return a
def patches():
    return [(AUTO + 4 * i, w) for i, w in enumerate(build().assemble())] + [(HOOK, 0x08000000 | (AUTO >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))




