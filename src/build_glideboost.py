"""Fast mode boost (ridden ground Angelus, toggle word 005BEE0C == 0) uses the gliding (wings-out dive) pose. The aerial boost forces the pitch parameter p of the blend setup (BGL, hook 001C8728 in FUN_001C868C,
dragon animation object s0 == 0041C140) to 0.0 so the game plays the dive / glide clip 28 (blend weight 1 - p / 0.3 below p = 0.3). BGL only did that on aerial stages (marker != 0); on a ground stage it now jumps
to GBL (005BCF00): Caim rides (003ACC94 == 2), fast mode and the L2 pressure byte (00342864 + the index byte 005747BA) >= 0x40 -> continue in BGL at the boosting label BCM (same target 0 and smooth change SP as in the
air); otherwise (standard mode / not boosting) the NB path (SP follows p, no change) or the plain exit."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib'); sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src')
from mipsasm import Asm
import build_aerialboost as AB
GB3 = 0x5BD140       # brake mode boost pose (cave): glide pose while she descends, the regular animation at the lowest point (FL, set by VUP2 in build_descend.py)
GB2 = 0x5BCFA0       # climb check (cave): pose pitch (+0xC4 of the pose block 0041BFC0) above 0.05 rad = she is gaining height -> the regular boost animation
def climb():
    a = Asm(GB2); L = AB.LAB['BGL']
    a.emit('lui', 't9', 0x5C); a.emit('lw', 't8', -0x121C, 't9'); a.emit('bne', 't8', 'zero', 'NBC'); a.emit('nop')                       # the L3 lock (build_specmove.py LOCK): no boost pose until L2 is pressed again
    a.emit('lui', 't8', 0x42); a.emit('lw', 't8', -0x3F7C, 't8'); a.emit('lui', 't9', 0x3D4C); a.emit('ori', 't9', 't9', 0xCCCD); a.emit('slt', 't8', 't9', 't8')   # t9 < pitch (positive floats order like signed ints)
    a.emit('lui', 't9', 0x5C); a.emit('bne', 't8', 'zero', 'NBC'); a.emit('nop'); a.emit('j', L['BCM']); a.emit('nop')
    a.label('NBC'); a.emit('j', L['NB']); a.emit('nop')
    return a
def gb3():
    FL = -0x1214                      # 005BEDEC lui 0x5C: 1 = she is not moving down (lowest point)
    a = Asm(GB3); L = AB.LAB['BGL']
    a.emit('lui', 't8', 0x57); a.emit('lbu', 't8', 0x47BA, 't8'); a.emit('lui', 't9', 0x34); a.emit('addu', 't8', 't8', 't9'); a.emit('lbu', 't8', 0x2864, 't8'); a.emit('sltiu', 't8', 't8', 0x40)
    a.emit('bne', 't8', 'zero', 'NB3'); a.emit('nop')
    a.emit('lui', 't9', 0x5C); a.emit('lw', 't8', FL, 't9'); a.emit('bne', 't8', 'zero', 'NB3'); a.emit('nop')
    a.emit('j', L['BCM']); a.emit('nop')
    a.label('NB3'); a.emit('lui', 't9', 0x5C); a.emit('j', L['NB']); a.emit('nop')
    return a
def build():
    AB.layout()
    L = AB.LAB['BGL']
    a = Asm(AB.GBL)
    a.emit('lui', 't9', 0x3B); a.emit('lw', 't8', -0x336C, 't9'); a.emit('addiu', 't8', 't8', -2); a.emit('bne', 't8', 'zero', 'OUTG'); a.emit('nop')
    a.emit('lui', 't9', 0x5C); a.emit('lw', 't8', AB.TGB, 't9'); a.emit('bne', 't8', 'zero', 'BMJ'); a.emit('nop')
    a.emit('lui', 't8', 0x57); a.emit('lbu', 't8', 0x47BA, 't8'); a.emit('lui', 't9', 0x34); a.emit('addu', 't8', 't8', 't9'); a.emit('lbu', 't8', 0x2864, 't8'); a.emit('sltiu', 't8', 't8', 0x40)
    a.emit('bne', 't8', 'zero', 'NBG'); a.emit('nop')
    a.emit('lbu', 't8', 0x2867, 't9'); a.emit('sltiu', 't8', 't8', 0xF0); a.emit('beq', 't8', 'zero', 'NBG'); a.emit('nop')       # left stick pulled fully back (raw y >= 0xF0): the regular boost animation (NB path)
    a.emit('j', GB2); a.emit('nop')                                                                                                    # not pulled back: GB2 checks for a climb
    a.label('NBG'); a.emit('lui', 't9', 0x5C); a.emit('j', L['NB']); a.emit('nop')
    a.label('BMJ'); a.emit('j', GB3); a.emit('nop')                                                                  # brake mode: GB3 (descent while boosting)
    a.label('OUTG'); a.emit('j', L['OUT']); a.emit('nop')
    return a
L3P, LOCK = -0x1220, -0x121C        # 005BEDE0 / 005BEDE4 (lui 0x5C)
def lockpart():
    """LP (005BC680, hook 001C09DC jal 001C3EBC -> jal LP, a1 = the pad struct, s0 = the dragon): FAST MODE (toggle word 005BEE0C == 0): an L3 press (the glide start; raw pad byte 0056CD82 bit 1, active low; previous state in
    word 005BEDE0) CANCELS the boost, even with L2 held: at the press edge the boost multiplier +0x3DE8 / +0x3DEC becomes 1.0, the glide momentum M (005BEFE0..E8) is NOT touched (the glide carries the boost speed for its whole run, until it ends or is cancelled) and LOCK (word 005BEDE4) is set. LOCK is cleared when the L2 pressure byte (00342864 + the index byte 005747BA) drops below 0x40 (L2 released); while it is set the L2 held bits (a1+8 and a1+0xC,
    bit 0x100) are cleared (no boost; GBL sees no boost pose either): L2 has to be released and pressed again. Standard mode: the lock is cleared. Ends with j PRE (the special part, build_specmove.py)."""
    import build_specmove as M
    a = Asm(M.LP)
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't9', -0x11F4, 't8'); a.emit('bne', 't9', 'zero', 'NOF'); a.emit('nop')
    a.emit('lui', 't9', 0x57); a.emit('lbu', 't9', -0x327E, 't9'); a.emit('andi', 't9', 't9', 2); a.emit('sltiu', 't9', 't9', 1)
    a.emit('lw', 't2', L3P, 't8'); a.emit('sw', 't9', L3P, 't8')
    a.emit('beq', 't9', 'zero', 'REL'); a.emit('nop'); a.emit('bne', 't2', 'zero', 'REL'); a.emit('nop')
    a.emit('lwc1', 'f0', 0x3DE8, 's0'); a.emit('lui', 'at', 0x3F80); a.emit('mtc1', 'at', 'f1'); a.emit('c.olt.s', 'f1', 'f0'); a.emit('bc1f', 'SETL'); a.emit('nop')
    a.emit('swc1', 'f1', 0x3DE8, 's0'); a.emit('swc1', 'f1', 0x3DEC, 's0')
    a.label('SETL'); a.emit('ori', 't9', 'zero', 1); a.emit('sw', 't9', LOCK, 't8')
    a.label('REL')
    a.emit('lui', 't9', 0x57); a.emit('lbu', 't9', 0x47BA, 't9'); a.emit('lui', 't2', 0x34); a.emit('addu', 't9', 't9', 't2'); a.emit('lbu', 't9', 0x2864, 't9'); a.emit('sltiu', 't9', 't9', 0x40)
    a.emit('beq', 't9', 'zero', 'CHK'); a.emit('nop'); a.emit('sw', 'zero', LOCK, 't8')
    a.label('CHK'); a.emit('lw', 't9', LOCK, 't8'); a.emit('beq', 't9', 'zero', 'GO'); a.emit('nop')
    a.emit('lw', 't9', 8, 'a1'); a.emit('lui', 't2', 0xFFFF); a.emit('ori', 't2', 't2', 0xFEFF); a.emit('and', 't9', 't9', 't2'); a.emit('sw', 't9', 8, 'a1')
    a.emit('lw', 't9', 12, 'a1'); a.emit('and', 't9', 't9', 't2'); a.emit('sw', 't9', 12, 'a1')
    a.emit('beq', 'zero', 'zero', 'GO'); a.emit('nop')
    a.label('NOF'); a.emit('sw', 'zero', LOCK, 't8'); a.emit('sw', 'zero', L3P, 't8')
    a.label('GO'); a.emit('j', 0x5BD200); a.emit('nop')                                  # L1C (build_descend.py): L1 ascends, its dodge bits are cleared, then PRE
    return a
def patches():
    w = build().assemble(); p = [(AB.GBL + 4 * i, x) for i, x in enumerate(w)]
    import build_specmove as M
    p += [(GB2 + 4 * i, x) for i, x in enumerate(climb().assemble())]
    p += [(GB3 + 4 * i, x) for i, x in enumerate(gb3().assemble())]
    p += [(GB2 + 4 * i, x) for i, x in enumerate(climb().assemble())]
    p += [(GB3 + 4 * i, x) for i, x in enumerate(gb3().assemble())]
    return p + [(M.LP + 4 * i, x) for i, x in enumerate(lockpart().assemble())]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
