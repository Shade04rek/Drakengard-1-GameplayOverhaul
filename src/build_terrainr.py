"""Terrain block radius: 32 on aerial stages (marker 00340DFC != 0), 14 (vanilla) on ground stages. Hook 00229CC0 (lui at,43A0 in FUN_00229BEC)
-> TRC (005BEA00): redoes the lui, sets t7 = -R, t8 = 64 + R, t9 = 36 + R; the six addiu of the window (229CC8/CCC/CD0, 229CF0/CF4, 229D08)
become addu with t7/t8/t9 (the registers are only live inside that straight run, no call in between)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
TRC = 0x5BEA00
RA, RG = 32, 14
def build():
    a = Asm(TRC)
    a.emit('lui', 'at', 0x43A0)
    a.emit('lui', 't0', 0x34); a.emit('lw', 't0', 0xDFC, 't0'); a.emit('beq', 't0', 'zero', 'GRD'); a.emit('nop')
    for r, v in (('t7', -RA), ('t8', 64 + RA), ('t9', 36 + RA)): a.emit('addiu', r, 'zero', v)
    a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('GRD')
    for r, v in (('t7', -RG), ('t8', 64 + RG), ('t9', 36 + RG)): a.emit('addiu', r, 'zero', v)
    a.label('OUT')
    a.emit('j', 0x229CC4); a.emit('nop')
    return a
def patches():
    p = [(TRC + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x229CC0, 0x08000000 | (TRC >> 2))]
    def addu(rd, rs, rt): return (rs << 21) | (rt << 16) | (rd << 11) | 0x21
    V0, V1, A0, T7, T8, T9 = 2, 3, 4, 15, 24, 25
    p += [(0x229CC8, addu(V1, V0, T7)), (0x229CCC, addu(A0, V0, T8)), (0x229CD0, addu(V0, V0, T9)),
          (0x229CF0, addu(V0, V1, T7)), (0x229CF4, addu(A0, V1, T8)), (0x229D08, addu(V1, V1, T9))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
