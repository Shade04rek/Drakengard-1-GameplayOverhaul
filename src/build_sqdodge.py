import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
SQ = 0x5BBE00           # moved 2026-10-28 from 005AF900 (grew)
RIGHT_FROM = 0x88        # left stick X (0x00 left .. 0x7F centre .. 0xFF right) above which the press is the Circle one
SQUARE_P, CIRCLE_P = 0x286F, 0x286D      # pressure bytes in the pad copy 00342850 (+0x14 + button index 0x0B / 9)
# Runs between T2 (00321A74) and the pad table cleanup 005B6D00, which uses T2's t2 (0x570000) and t5 (the B0 entry)
# and then 00321A7C, which uses t8 (0x340000). Only t3, t4, t6, t9 are used here; t2, t5, t8 are left as they are.
# Square and Circle are the same button: stick right -> the press goes to Circle (right dodge), stick left / neutral ->
# the press goes to Square (left dodge).
def move(a, src, dst, tag):
    a.emit('lbu', 't4', src, 't3')
    a.emit('beq', 't4', 'zero', 'OUT'); a.emit('nop')
    a.emit('lbu', 't6', dst, 't3')
    a.emit('sltu', 't9', 't6', 't4'); a.emit('beq', 't9', 'zero', tag); a.emit('nop')
    a.emit('sb', 't4', dst, 't3')                                   # the other button gets this press
    a.label(tag)
    a.emit('sb', 'zero', src, 't3')
    a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
SAVE = -0x4020           # 005BBFE0..EB (lui 0x5C): T2's t3 / t4 / t6, which later T2 caves read (AIRC at 00341C94 needs t3 and t6)
def build():
    a = Asm(SQ)
    a.emit('lui', 't9', 0x5C)
    a.emit('sw', 't3', SAVE, 't9'); a.emit('sw', 't4', SAVE + 4, 't9'); a.emit('sw', 't6', SAVE + 8, 't9')
    a.emit('lui', 't3', 0x34)
    # riding Angelus on the ground (Caim +0x6B4 == 2, aerial marker 00340DFC == 0): her Square / Circle stay vanilla
    a.emit('lw', 't4', 0x0DFC, 't3'); a.emit('bne', 't4', 'zero', 'FOOT'); a.emit('nop')
    a.emit('lui', 't4', 0x3B); a.emit('lw', 't4', -0x336C, 't4')    # 003ACC94 = Caim +0x6B4
    a.emit('addiu', 't6', 'zero', 2); a.emit('beq', 't4', 't6', 'OUT'); a.emit('nop')
    a.label('FOOT')
    # 2026-10-28: stick at rest (both axes within 0x30 of 0x80) -> no remap: Square = its left dodge, Circle = its right
    # dodge (vanilla). Otherwise the stick side decides (x >= 0x80 = right, the same split the roll cave TR uses).
    for off in (0x2866, 0x2867):
        a.emit('lbu', 't4', off, 't3'); a.emit('addiu', 't4', 't4', -0x80)
        a.emit('sra', 't6', 't4', 31); a.emit('xor', 't4', 't4', 't6'); a.emit('subu', 't4', 't4', 't6')
        a.emit('sltiu', 't4', 't4', 0x30); a.emit('beq', 't4', 'zero', 'MOVED'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('MOVED')
    a.emit('lbu', 't4', 0x2866, 't3')                              # left stick X (pad copy +0x16)
    a.emit('sltiu', 't4', 't4', 0x80)
    a.emit('bne', 't4', 'zero', 'LEFT'); a.emit('nop')
    move(a, SQUARE_P, CIRCLE_P, 'K1')                               # right: Square -> Circle
    a.label('LEFT')
    move(a, CIRCLE_P, SQUARE_P, 'K2')                               # left / neutral: Circle -> Square
    a.label('OUT')
    a.emit('lui', 't9', 0x5C)
    a.emit('lw', 't3', SAVE, 't9'); a.emit('lw', 't4', SAVE + 4, 't9')
    a.emit('j', 0x5B6D00); a.emit('lw', 't6', SAVE + 8, 't9')
    return a
def patches():
    return [(SQ + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x321A74, 0x08000000 | (SQ >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
