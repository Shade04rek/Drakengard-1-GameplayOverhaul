"""Builds the ISO patch of the mod (2026-11-11): reads the vanilla SLUS_207.32 out of an ISO, bakes the pnach into it and writes
  isopatch/drakengard_isopatch.py   = a standalone patcher (python3, no other tools) that contains only the DIFFERENCE (the mod's own words, zlib + base64), no game data.
How the pnach is baked (all addresses are the ones of the pnach):
  * code segment (0x120000..0x341A18) and the file-backed data (0x341A80..) words: written into the ELF file image (patch=1 and patch=0);
  * the cave area 0x5A0000..0x5C0000 was BSS (cleared by crt0 at 0x120018). The data segment is made file-backed up to 0x5C0000 (p_filesz = 0x27E580, 0x5370B zero bytes inserted at file offset 0x44D8F5,
    e_shoff moved) and crt0 clears only 0x5C0000..0x6B4414 (0x120008 lui v0,0x5C; 0x120010 addiu v0,v0,0); the cave words are written into that extension;
  * patch=1 words in the data area / the gap between the segments (the game may rewrite them) go to a table that the per-frame hook re-applies: 0x127334 (the HUD hook, pnach: j 0x5A1000) becomes j APPLY
    (0x5B8A00), which stores the table (0x5B8B00: addr / value pairs, bit 31 of the address = halfword) and then jumps to 0x5A1000 as before.
Not part of the ISO: the pnach line gsaspectratio=16:9 (set Widescreen in PCSX2)."""
import re, struct, sys, os, zlib, base64, hashlib
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\2b266e65fa509e93\fc7fa988-ea8f-4fa2-b5eb-1c7f92e06e80\scratchpad')
import iso as ISO
PNACH = r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\SLUS-20732_9679D44C.pnach'
VANILLA = r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\Drakengard (USA) original.iso'
OUT = r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\isopatch'
SEG1_OFF, SEG1_VA, SEG1_SZ = 0x1000, 0x120000, 0x221A18
SEG2_OFF, SEG2_VA, SEG2_FILESZ, SEG2_MEMSZ = 0x222A80, 0x341A80, 0x22AE75, 0x372994
CAVE_LO, CAVE_HI = 0x5A0000, 0x5C0000
INS_AT = SEG2_OFF + SEG2_FILESZ            # 0x44D8F5
INS_N = CAVE_HI - (SEG2_VA + SEG2_FILESZ)  # 0x5370B
APPLY, TABLE = 0x5B8A00, 0x5B8B00
HOOK = 0x127334
def fileoff(a):
    if SEG1_VA <= a < SEG1_VA + SEG1_SZ: return a - SEG1_VA + SEG1_OFF
    if SEG2_VA <= a < CAVE_HI: return a - SEG2_VA + SEG2_OFF
    return None
def read_elf():
    with open(VANILLA, 'rb') as f:
        lba, size, p, root = ISO.find_file(f, 'SLUS_207.32'); f.seek(lba * 2048); e = f.read(size)
    assert ISO.crc_elf(e) == 0x9679D44C
    return e
def main():
    e = read_elf()
    ext = bytearray(e[:INS_AT] + bytes(INS_N) + e[INS_AT:])
    base = bytes(ext)
    struct.pack_into('<I', ext, 0x20, struct.unpack_from('<I', e, 0x20)[0] + INS_N)         # e_shoff
    ph = struct.unpack_from('<I', e, 0x1C)[0]
    struct.pack_into('<I', ext, ph + 2 * 32 + 16, CAVE_HI - SEG2_VA)                          # p_filesz of the data segment
    # pnach entries
    ents = {}
    for l in open(PNACH, encoding='utf-8-sig').read().split('\n'):
        m = re.match(r'^patch=([01]),EE,([0-9A-Fa-f]{8}),(word|short),([0-9A-Fa-f]+)', l.strip())
        if m: ents[int(m.group(2), 16)] = (int(m.group(1)), m.group(3), int(m.group(4), 16))
    table = []
    nb = {'code': 0, 'data': 0, 'cave': 0, 'table': 0, 'gap': 0}
    for a, (pm, ty, v) in sorted(ents.items()):
        if a == HOOK: continue
        sz = 4 if ty == 'word' else 2
        fo = fileoff(a)
        if fo is not None:
            ext[fo:fo + sz] = struct.pack('<I' if sz == 4 else '<H', v)
            nb['cave' if a >= CAVE_LO else ('code' if a < SEG2_VA else 'data')] += 1
        if pm == 1 and not (a < SEG2_VA and fo is not None) and not (CAVE_LO <= a < CAVE_HI):     # data area / the gap: re-applied every frame
            table.append((a | (0x80000000 if sz == 2 else 0), v)); nb['table'] += 1
            if fo is None: nb['gap'] += 1
    # crt0: clear only 0x5C0000..0x6B4414
    struct.pack_into('<I', ext, fileoff(0x120008), 0x3C02005C); struct.pack_into('<I', ext, fileoff(0x120010), 0x24420000)
    # applier
    for a in list(ents):
        assert not (APPLY <= a < TABLE + 8 * len(table) + 16), hex(a)
    tend = TABLE + 8 * len(table)
    a = Asm(APPLY)
    a.emit('lui', 't0', TABLE >> 16); a.emit('ori', 't0', 't0', TABLE & 0xFFFF); a.emit('lui', 't1', tend >> 16); a.emit('ori', 't1', 't1', tend & 0xFFFF)
    a.label('LP'); a.emit('beq', 't0', 't1', 'DN'); a.emit('nop')
    a.emit('lw', 't2', 0, 't0'); a.emit('lw', 't3', 4, 't0')
    a.emit('srl', 't4', 't2', 31); a.emit('bne', 't4', 'zero', 'HW'); a.emit('nop')
    a.emit('sw', 't3', 0, 't2'); a.emit('beq', 'zero', 'zero', 'NX'); a.emit('nop')
    a.label('HW'); a.emit('sll', 't2', 't2', 1); a.emit('srl', 't2', 't2', 1); a.emit('sh', 't3', 0, 't2')
    a.label('NX'); a.emit('addiu', 't0', 't0', 8); a.emit('beq', 'zero', 'zero', 'LP'); a.emit('nop')
    a.label('DN'); a.emit('j', 0x5A1000); a.emit('nop')
    w = a.assemble(); assert APPLY + 4 * len(w) <= TABLE
    for i, x in enumerate(w): struct.pack_into('<I', ext, fileoff(APPLY + 4 * i), x)
    for i, (ad, v) in enumerate(table): struct.pack_into('<II', ext, fileoff(TABLE + 8 * i), ad, v)
    struct.pack_into('<I', ext, fileoff(HOOK), 0x08000000 | (APPLY >> 2))
    assert tend < 0x5BA800
    # delta
    runs = []; i = 0; n = len(ext)
    while i < n:
        if ext[i] != base[i]:
            j = i
            while j < n and (ext[j] != base[j] or (j + 1 < n and ext[j + 1] != base[j + 1]) or (j + 2 < n and ext[j + 2] != base[j + 2])): j += 1
            runs.append((i, bytes(ext[i:j]))); i = j
        else: i += 1
    blob = b''.join(struct.pack('<II', o, len(d)) + d for o, d in runs)
    z = base64.b64encode(zlib.compress(blob, 9)).decode()
    print('entries', len(ents), nb, 'table', len(table), 'runs', len(runs), 'delta bytes', len(blob), 'b64', len(z), 'new elf size', len(ext))
    os.makedirs(OUT, exist_ok=True)
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'isopatcher_template.py'), encoding='utf-8').read()
    tpl = tpl.replace('@@DELTA@@', z).replace('@@INS_AT@@', hex(INS_AT)).replace('@@INS_N@@', hex(INS_N)).replace('@@NEWSIZE@@', str(len(ext)))
    tpl = tpl.replace('@@NEWCRC@@', '%08X' % ISO.crc_elf(bytes(ext) + bytes((-len(ext)) % 4)))
    open(os.path.join(OUT, 'drakengard_isopatch.py'), 'w', encoding='utf-8', newline='\n').write(tpl)
    return ext, ents, table
if __name__ == '__main__':
    main()

