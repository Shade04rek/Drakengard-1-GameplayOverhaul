#!/usr/bin/env python3
"""Port of the NTSC-U pnach to the European executable (SLES_523.22, CRC 79585776).

  python pal_port.py [--report]

Reads the NTSC-U and PAL executables from the two ISOs (paths below), aligns their code, and writes
SLES-52322_79585776.pnach next to the NTSC-U pnach.
 * hook words (they overwrite original game code / data) go to the matching PAL address;
 * cave blocks (code / data in free memory) are moved: the ones in the bss (0x5A0000..0x5BFFFF) by +0x5000, the
   ones in code padding / data padding into a pool behind them (0x5C4000..);
 * every address the patched code forms (lui + addiu/ori/load/store, j/jal, branches, gp-relative accesses) is
   translated (game code: code alignment table, game data: data table, mod memory: block map).
"""
import bisect, collections, pickle, re, struct, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..', '..')
NTSC_ISO = os.path.join(R, 'drakengard_mod', 'Drakengard (USA) original.iso')
PAL_ISO = os.path.join(R, 'Drakengard (Europe) (En,Fr,De,Es,It).iso')
PNACH_IN = os.path.join(HERE, '..', 'SLUS-20732_9679D44C.pnach')
PNACH_OUT = os.path.join(HERE, '..', 'SLES-52322_79585776.pnach')
SEC = 2048
TEXT_LO, TEXT_HI = 0x120000, 0x341A18
DATA_LO, DATA_HI = 0x341A80, 0x6B4414
CAVE_LO, CAVE_HI, CAVE_SHIFT = 0x5A0000, 0x5C0000, 0x4E80          # the game's bss variables are 0x4E80 further up in the PAL executable
POOL = 0x5BEE20
S16 = lambda x: x - 0x10000 if x & 0x8000 else x


def read_elf(path):
    f = open(path, 'rb')
    f.seek(16 * SEC); pvd = f.read(SEC)
    root_lba = struct.unpack_from('<I', pvd, 158)[0]; root_len = struct.unpack_from('<I', pvd, 166)[0]
    f.seek(root_lba * SEC); data = f.read(root_len); p = 0; ents = []
    while p < len(data):
        l = data[p]
        if l == 0: p = (p // SEC + 1) * SEC; continue
        lba = struct.unpack_from('<I', data, p + 2)[0]; size = struct.unpack_from('<I', data, p + 10)[0]
        ents.append((data[p + 33:p + 33 + data[p + 32]].decode('latin1'), lba, size)); p += l
    sysf = [e for e in ents if e[0].upper().startswith('SYSTEM.CNF')][0]
    f.seek(sysf[1] * SEC); cnf = f.read(sysf[2]).decode('latin1')
    name = re.search(r'BOOT2\s*=\s*cdrom0:\\?([^;\s]+)', cnf)[1]
    e = [x for x in ents if x[0].upper().startswith(name.upper())][0]
    f.seek(e[1] * SEC); return f.read(e[2])


class Elf:
    def __init__(self, raw):
        self.raw = raw
        phoff = struct.unpack_from('<I', raw, 28)[0]; phes, phn = struct.unpack_from('<HH', raw, 42)
        self.segs = []
        for i in range(phn):
            t, off, va, pa, fsz, msz, fl, al = struct.unpack_from('<8I', raw, phoff + i * phes)
            if t == 1: self.segs.append((va, fsz, msz, off))

    def w(self, a):
        """original word at address a (None = outside the image, 0 = bss / zero)"""
        for va, fsz, msz, off in self.segs:
            if va <= a < va + msz:
                return struct.unpack_from('<I', self.raw, off + a - va)[0] if a - va + 4 <= fsz else 0
        return None

    def gp(self):                                          # crt0: lui a0,hi; addiu a0,a0,lo; ... daddu gp,a0,zero
        hi = self.w(0x120034) & 0xFFFF; lo = S16(self.w(0x120048) & 0xFFFF)
        return (hi << 16) + lo


IMM = {0xF, 8, 9, 0xA, 0xB, 0xC, 0xD, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x28, 0x29, 0x2A, 0x2B, 0x2E, 0x31, 0x39, 0x37, 0x3F, 0x1E, 0x1F, 0x35, 0x3D}
MEM = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2E, 0x31, 0x39, 0x37, 0x3F, 0x1E, 0x1F, 0x35, 0x3D}


def mk(w):
    op = w >> 26
    if op in (2, 3): return w & 0xFC000000
    if op in IMM: return w & 0xFFFF0000
    return w


def load_anchors(ntsc, pal, K=10):
    NT = [ntsc.w(TEXT_LO + 4 * i) for i in range((TEXT_HI - TEXT_LO) // 4)]
    PL = [pal.w(TEXT_LO + 4 * i) for i in range((TEXT_HI + 0x4000 - TEXT_LO) // 4)]
    idx = collections.defaultdict(list)
    for i in range(len(PL) - K): idx[tuple(mk(x) for x in PL[i:i + K])].append(i)
    anchors = []
    for i in range(len(NT) - K):
        key = tuple(mk(x) for x in NT[i:i + K])
        if len(set(key)) < 4: continue
        c = idx.get(key)
        if c and len(c) == 1: anchors.append((i, c[0] - i))
    return NT, PL, anchors


def data_pairs(NT, PL, anchors, ntsc_gp=None):
    m = collections.defaultdict(collections.Counter)
    for i, d in anchors:
        for j in range(i, i + 8):
            w = NT[j]; pw = PL[j + d]
            if (w >> 26) != 0xF or (pw >> 26) != 0xF: continue
            hi = w & 0xFFFF
            if not (0x34 <= hi <= 0x6B): continue
            for k in (1, 2, 3):
                x = NT[j + k]; y = PL[j + d + k]
                if (x >> 26) in MEM | {9, 0xD} and (y >> 26) == (x >> 26) and ((x >> 21) & 31) == ((w >> 16) & 31) and ((y >> 21) & 31) == ((pw >> 16) & 31):
                    f = lambda h, o: ((h << 16) + (S16(o & 0xFFFF) if (o >> 26) != 0xD else (o & 0xFFFF))) & 0xFFFFFFFF
                    an = f(hi, x); ap = f(pw & 0xFFFF, y)
                    if DATA_LO <= an < DATA_HI: m[an][ap] += 1
                    break
    return {a: c.most_common(1)[0][0] for a, c in m.items() if len(c) == 1 and 0x3F00 <= c.most_common(1)[0][0] - a <= 0x5000}


class Mapper:
    def __init__(self, ntsc, pal):
        self.n, self.p = ntsc, pal
        cache = os.path.join(os.environ.get('TEMP', '.'), 'pal_anchor_cache2.pkl')
        if os.path.exists(cache):
            self.NT, self.PL, self.anchors, self.dpairs = pickle.load(open(cache, 'rb'))
        else:
            self.NT, self.PL, self.anchors = load_anchors(ntsc, pal)
            self.dpairs = data_pairs(self.NT, self.PL, self.anchors)
            pickle.dump((self.NT, self.PL, self.anchors, self.dpairs), open(cache, 'wb'))
        self.akeys = [a for a, _ in self.anchors]
        self.dkeys = sorted(self.dpairs)
        self.gp_n, self.gp_p = ntsc.gp(), pal.gp()

    def code(self, a):
        i = (a - TEXT_LO) // 4
        j = bisect.bisect_left(self.akeys, i)
        cands = []
        for k in range(j - 6, j + 6):
            if 0 <= k < len(self.anchors): cands.append(self.anchors[k][1])
        best = None; bs = -1
        for d in dict.fromkeys(cands):
            s = 0
            for t in range(-4, 5):
                if 0 <= i + t < len(self.NT) and 0 <= i + t + d < len(self.PL):
                    s += mk(self.NT[i + t]) == mk(self.PL[i + t + d])
            if s > bs: bs, best = s, d
        return None if best is None or bs < 4 else a + 4 * best

    def data(self, a):
        j = bisect.bisect_right(self.dkeys, a)
        cands = []
        for k in (j - 1, j):
            if 0 <= k < len(self.dkeys): cands.append(self.dpairs[self.dkeys[k]] - self.dkeys[k])
        if not cands: return None
        best = cands[0]; bs = -1
        for d in dict.fromkeys(cands):
            s = 0
            for t in range(0, 0x20, 4):
                x = self.n.w(a + t); y = self.p.w(a + t + d)
                if x not in (None, 0) and x == y: s += 1
            if s > bs: bs, best = s, d
        if bs < 3:                                           # the content of the neighbours' deltas does not fit: search nearby
            base = cands[0]
            sb = 0; sbd = None
            for d in range(base - 0x600, base + 0x600, 4):
                s = 0
                for t in range(0, 0x30, 4):
                    x = self.n.w(a + t); y = self.p.w(a + t + d)
                    if x not in (None, 0) and x == y: s += 1
                if s > sb: sb, sbd = s, d
            if sbd is not None and sb >= 3: best = sbd; bs = sb
        return a + best


# ------------------------------------------------------------------ patch model
def load_pnach(path):
    lines = open(path, encoding='utf-8').read().replace('\r\n', '\n').split('\n')
    W = {}; SH = {}
    for l in lines:
        m = re.match(r'patch=1,EE,([0-9A-Fa-f]{8}),(word|short),([0-9A-Fa-f]+)', l)
        if m:
            (W if m[2] == 'word' else SH)[int(m[1], 16)] = int(m[3], 16)
    return lines, W, SH


def decode_targets(W, a, w):
    """control-flow target of the word at a, or None"""
    op = w >> 26
    if op in (2, 3): return ((a & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
    if op in (4, 5, 6, 7, 0x14, 0x15, 1) or (op == 0x11 and ((w >> 21) & 31) == 8 and (w >> 16) & 3 in (0, 1, 2, 3)):
        return a + 4 + 4 * S16(w & 0xFFFF)
    return None


def is_branch(w):
    op = w >> 26
    return op in (4, 5, 6, 7, 0x14, 0x15, 1) or (op == 0x11 and ((w >> 21) & 31) == 8)


def lui_groups(W, code):
    """[(lui_addr, reg, [(user_addr, kind)])]: lui rX,hi (hi in the address range) and every use of rX that its value reaches, following jumps and branches
    (the lui and its users are often in different cave blocks)"""
    out = []
    CALLER = set(range(1, 16)) | {24, 25}
    for a in sorted(code):
        w = W[a]
        if (w >> 26) != 0xF: continue
        rt = (w >> 16) & 31; hi = w & 0xFFFF
        if rt == 0 or not (0x12 <= hi <= 0x6B): continue
        users = []; seen_u = set(); visited = set(); stack = [a + 4]; budget = 600

        def check(b):
            """examine the word at b: record a use; True when the register's value ends here"""
            x = W[b]; op = x >> 26; rs = (x >> 21) & 31; xt = (x >> 16) & 31
            if rs == rt and (op in MEM or op in (9, 0xD)):
                if b not in seen_u: seen_u.add(b); users.append((b, 'mem' if op in MEM else ('addiu' if op == 9 else 'ori')))
                if xt == rt and (op in (9, 0xD) or op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x1E)): return True
                return False
            if xt == rt and op in (9, 0xD, 0xA, 0xB, 0xC, 0xF, 0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x1E): return True
            if op == 0 and ((x >> 11) & 31) == rt and (x & 63) not in (8, 9, 0x18, 0x19, 0x1A, 0x1B): return True
            return False

        while stack and budget > 0:
            b = stack.pop()
            while b in W and b in code and b not in visited and budget > 0:
                budget -= 1; visited.add(b); x = W[b]; op = x >> 26
                is_j = op in (2, 3) or (op == 0 and (x & 63) in (8, 9))
                if is_j or is_branch(x):
                    ds = b + 4                                                  # the delay slot runs before the transfer
                    if ds in W and check(ds): break
                    if op in (3,) or (op == 0 and (x & 63) == 9):               # a call: caller-saved registers die
                        if rt in CALLER: break
                        stack.append(b + 8); break
                    if op == 2 or (op == 0 and (x & 63) == 8):
                        if op == 2: stack.append(P_target(b, x))
                        break
                    stack.append(P_target(b, x)); stack.append(b + 8); break
                if check(b): break
                b += 4
        if users: out.append((a, rt, sorted(users)))
    return out


def P_target(a, x):
    t = decode_targets(None, a, x)
    return t


def main():
    ntsc = Elf(read_elf(NTSC_ISO)); pal = Elf(read_elf(PAL_ISO))
    M = Mapper(ntsc, pal)
    lines, W, SH = load_pnach(PNACH_IN)
    print('NTSC words', len(W), 'shorts', len(SH), '| anchors', len(M.anchors), 'data pairs', len(M.dpairs))
    Z = sorted(a for a in W if ntsc.w(a) in (0, None))
    blocks = []; s = e = None
    for a in Z:
        if s is None: s = e = a
        elif a - e <= 0x10: e = a
        else: blocks.append([s, e]); s = e = a
    if s is not None: blocks.append([s, e])
    groups_all = lui_groups(W, set(W))
    targets = set()
    for a, w in W.items():
        t_ = decode_targets(W, a, w)
        if t_ is not None: targets.add(t_)
    def user_addr(la, b, kind):
        hi = W[la] & 0xFFFF; x = W[b]
        off = S16(x & 0xFFFF) if kind != 'ori' else (x & 0xFFFF)
        return ((hi << 16) + off) & 0xFFFFFFFF
    for la, rt, users in groups_all:
        for b, kind in users: targets.add(user_addr(la, b, kind))
    cave = []
    for s, e in blocks:
        n = sum(1 for a in Z if s <= a <= e)
        if s >= 0x56CB80 or n >= 3 or any(s <= t_ <= e + 3 for t_ in targets): cave.append((s, e))
    cave_words = {a for a in W if any(s <= a <= e for s, e in cave)}
    hook_words = set(W) - cave_words
    print('blocks', len(blocks), 'cave blocks', len(cave), 'cave words', len(cave_words), 'hook words', len(hook_words))

    # ---- where the caves go
    assigned = []                                   # PAL ranges taken
    pool = [POOL]; pool34 = [0x344E00]
    def pal_free(c, nbytes):
        for k in range(0, nbytes, 4):
            if pal.w(c + k) not in (0, None): return False
        return not any(c < y and x < c + nbytes for x, y in assigned)
    def pool_alloc(nbytes, align=16):
        c = (pool[0] + align - 1) & ~(align - 1); pool[0] = c + nbytes
        assigned.append((c, c + nbytes)); return c
    def place(s, e):
        nb = e + 4 - s
        if CAVE_LO <= s < CAVE_HI:
            c = s + CAVE_SHIFT; assigned.append((c, c + nb)); return c
        c = None
        if TEXT_LO <= s and e < TEXT_HI: c = M.code(s); c2 = M.code(e)
        elif DATA_LO <= s and e < 0x56CB80: c = M.data(s); c2 = M.data(e)
        if c is not None and c2 == c + (e - s) and pal_free(c, nb):
            assigned.append((c, c + nb)); return c
        return pool_alloc(nb)
    bmap = []
    for s, e in cave: bmap.append((s, e + 3, place(s, e)))
    bstarts = [b[0] for b in bmap]
    def block_of(a):
        i = bisect.bisect_right(bstarts, a) - 1
        if i >= 0 and bmap[i][0] <= a <= bmap[i][1]: return bmap[i]
        return None
    scratch = set()
    for la, rt, users in groups_all:
        for b, kind in users:
            A = user_addr(la, b, kind)
            if TEXT_LO <= A < TEXT_HI and not block_of(A) and kind == 'mem': scratch.add(A)
    clusters = []
    for A in sorted(scratch):
        if clusters and A - clusters[-1][1] <= 0x40: clusters[-1][1] = A
        else: clusters.append([A, A])
    smap = [(s, e + 3, place(s, e)) for s, e in clusters]
    sstarts = [b[0] for b in smap]
    print('cave blocks placed: in place of their PAL equivalent %d, in the pool %d | scratch clusters %d | pool end 0x%X' % (
        sum(1 for (s, e, c) in bmap if not (CAVE_LO <= s < CAVE_HI) and c < POOL), sum(1 for (s, e, c) in bmap if c >= POOL), len(clusters), pool[0]))

    cave_scratch = sorted({user_addr(la, b, kind) for la, rt, users in groups_all for b, kind in users
                           if CAVE_LO <= user_addr(la, b, kind) < CAVE_HI and user_addr(la, b, kind) not in W})
    gap = [0x5AE800]; GAP_END = 0x5AF000                 # free words of the NTSC cave region (they move by CAVE_SHIFT like the caves)
    over = {}                                       # scratch words moved (to make the lui windows fit)
    notes = []
    bad = collections.Counter()

    def T(A, why):
        if A in over: return over[A]
        b = block_of(A)
        if b: return b[2] + (A - b[0])
        i = bisect.bisect_right(sstarts, A) - 1
        if i >= 0 and smap[i][0] <= A <= smap[i][1]: return smap[i][2] + (A - smap[i][0])
        if CAVE_LO <= A < CAVE_HI: return A + CAVE_SHIFT
        if TEXT_LO <= A < TEXT_HI: r = M.code(A)
        elif DATA_LO <= A < DATA_HI: r = M.data(A)
        else: r = None
        if r is None: bad[why] += 1; notes.append((why, A))
        return r

    newaddr = {}
    for a in W:
        b = block_of(a)
        if b: newaddr[a] = b[2] + (a - b[0])
        else:
            r = M.code(a) if TEXT_LO <= a < TEXT_HI else (M.data(a) if DATA_LO <= a < DATA_HI else None)
            newaddr[a] = r
            if r is None: bad['hook address'] += 1; notes.append(('hook address', a))

    # ---- code words
    entry = set()
    for a in hook_words:
        t_ = decode_targets(W, a, W[a])
        if t_ is not None and t_ in cave_words: entry.add(t_)
    seen = set(); flow = set(); stack = list(entry)
    while stack:
        a = stack.pop()
        while a in cave_words and a not in flow:
            flow.add(a); seen.add(a); w = W[a]; t_ = decode_targets(W, a, w); op = w >> 26
            if t_ is not None and t_ in cave_words and t_ not in flow: stack.append(t_)
            if op == 2 or (op == 0 and (w & 63) == 8):
                # the delay slot is code too, but it can also be a jump target of its own (the slot of one j is the entry of another path): it is not marked as 'flowed'
                if a + 4 in cave_words:
                    seen.add(a + 4)
                    t2 = decode_targets(W, a + 4, W[a + 4])
                    if t2 is not None and t2 in cave_words and t2 not in flow: stack.append(t2)
                break
            a += 4
    flowed = set(hook_words) | seen
    # code that no traced path reaches (entered through registers / tables) is translated too; data patches into game objects (0x3AD000..0x59FFFF) are not code
    extra = {a for a in cave_words if a not in seen and not (0x3AD000 <= a < 0x5A0000)}
    code = set(hook_words) | seen | extra
    print('code words: traced %d + untraced cave words treated as code %d' % (len(flowed), len(extra)))
    print('code words: hooks', len(hook_words), '+ reachable cave words', len(seen), '| cave words not reached (data / dead)', len(cave_words) - len(seen))
    groups = lui_groups(W, code)
    gp_n, gp_p = M.gp_n, M.gp_p

    def addr_use(b, kind):
        # True when the register formed at b (lui + addiu / ori) is later used as an address: base of a load / store, jr / jalr, or an argument register of a call
        if kind == 'mem': return True
        x = W[b]; rd = (x >> 16) & 31
        for j in range(1, 40):
            c = b + 4 * j
            if c not in W: break
            y = W[c]; op = y >> 26; rs = (y >> 21) & 31; rt_ = (y >> 16) & 31
            if rs == rd and op in MEM: return True
            if op == 0 and (y & 63) in (8, 9) and rs == rd: return True
            if op == 0 and (y & 63) in (0x20, 0x21, 0x2C, 0x2D) and (rs == rd or rt_ == rd): return True            # pointer + index
            if op in (2, 3) and rd in (4, 5, 6, 7): return True
            if op == 0 and (y & 63) == 9 and rd in (4, 5, 6, 7): return True
            if (op in (9, 0xD, 0xF, 0x20, 0x21, 0x23, 0x24, 0x25) and rt_ == rd) or (op == 0 and ((y >> 11) & 31) == rd and (y & 63) not in (8, 9)):
                if not (op in (9, 0xD) and rs == rd): break
            if op == 0 and (y & 63) == 8 and rs == 31: break
        return False

    # addresses that are certainly addresses (some user treats them as such); a constant equal to one of them is an address wherever it is used (identity checks)
    known_addr = set()
    for la_, rt_, users_ in groups:
        for b_, kind_ in users_:
            A_ = user_addr(la_, b_, kind_)
            if kind_ == 'mem' or addr_use(b_, kind_): known_addr.add(A_)
    known_addr_sorted = sorted(known_addr)
    def near_known(A):
        i_ = bisect.bisect_left(known_addr_sorted, A)
        return any(0 <= k_ < len(known_addr_sorted) and abs(known_addr_sorted[k_] - A) <= 0x40 for k_ in (i_ - 1, i_)) or A in known_addr

    def translate():
        new = dict(W); conflicts = []
        for a in sorted(code):
            w = W[a]; op = w >> 26
            if op in MEM | {9} and ((w >> 21) & 31) == 28:
                A = gp_n + S16(w & 0xFFFF)
                if DATA_LO <= A < DATA_HI:
                    r = T(A, 'gp')
                    if r is not None:
                        off = r - gp_p
                        if -0x8000 <= off < 0x8000: new[a] = (w & 0xFFFF0000) | (off & 0xFFFF)
                        else: bad['gp range'] += 1
        for la, rt, users in groups:
            res = [(b, kind, user_addr(la, b, kind)) for b, kind in users]
            if not all(TEXT_LO <= A < DATA_HI for b, kind, A in res): continue
            acc = [addr_use(b, kind) or (CAVE_LO <= A < CAVE_HI) or A in M.dpairs or near_known(A) or (TEXT_LO <= A < TEXT_HI and ntsc.w(A) not in (0, None) and kind != 'mem')
                   for b, kind, A in res]      # constants inside the mod's own memory, addresses the game code itself uses (object identity checks) and code addresses are addresses
            if not any(acc): continue                                   # a constant that only looks like an address (flag masks such as 0x400080)
            if not all(acc): notes.append(('lui group with address and constant users', la)); continue
            news = [T(A, 'lui-pair') for b, kind, A in res]
            if any(r is None for r in news): continue
            his = set(((r + 0x8000) >> 16) if kind != 'ori' else (r >> 16) for (b, kind, A), r in zip(res, news))
            if len(his) != 1: conflicts.append((la, res, news)); continue
            h = his.pop()
            new[la] = (W[la] & 0xFFFF0000) | h
            for (b, kind, A), r in zip(res, news):
                new[b] = (W[b] & 0xFFFF0000) | ((r - (h << 16)) & 0xFFFF)
        for a in sorted(code):
            w = W[a]; op = w >> 26
            if op in (2, 3):
                t_ = decode_targets(W, a, w); r = T(t_, 'jump')
                if r is not None: new[a] = (op << 26) | ((r >> 2) & 0x3FFFFFF)
            elif is_branch(w) and a in flowed:
                t_ = decode_targets(W, a, w); ba = block_of(a); bt = block_of(t_)
                if ba and bt and ba == bt: continue
                na = newaddr[a]; r = T(t_, 'branch')
                if r is None or na is None: continue
                rel = (r - (na + 4)) // 4
                if -0x8000 <= rel < 0x8000: new[a] = (w & 0xFFFF0000) | (rel & 0xFFFF)
                else: bad['branch range'] += 1; notes.append(('branch range', a))
        return new, conflicts

    for it in range(12):
        bad.clear(); notes.clear()
        new, conflicts = translate()
        if not conflicts: break
        fixed = 0
        def movable(A): return A not in W and (CAVE_LO <= A < CAVE_HI or any(s <= A <= e for s, e, c in smap))
        for la, res, news in conflicts:
            # choose the window (the lui's high half) that all NON-movable users fit; movable scratch words then go into it
            best = None
            hs = sorted(set(((r + 0x8000) >> 16) for r in news) | set(((r + 0x8000) >> 16) + d for r in news for d in (-1, 1)))
            for h in hs:
                win = (h * 0x10000 - 0x8000, h * 0x10000 + 0x7FFF)
                imm = [(A, r) for (b, kind, A), r in zip(res, news) if not movable(A)]
                ok_imm = sum(1 for A, r in imm if win[0] <= r <= win[1])
                placeable = (win[0] <= (gap[0] + 3 & ~3) + CAVE_SHIFT <= win[1] and gap[0] < GAP_END) or (win[0] <= (pool[0] + 3 & ~3) <= win[1])
                score = (ok_imm == len(imm), ok_imm, placeable, -h)
                if best is None or score > best[0]: best = (score, h, win)
            _, h, win = best
            for (b, kind, A), r in zip(res, news):
                cur = over.get(A, r)
                if win[0] <= cur <= win[1]: continue
                if not movable(A): notes.append(('lui conflict (an immovable word does not fit)', la)); continue
                c = (gap[0] + 3) & ~3
                if win[0] <= c + CAVE_SHIFT <= win[1] and c < GAP_END:
                    over[A] = c + CAVE_SHIFT; gap[0] = c + 4; fixed += 1
                else:
                    c = (pool[0] + 3) & ~3
                    if win[0] <= c <= win[1]: pool[0] = c + 4; over[A] = c; fixed += 1
                    else: notes.append(('lui conflict (no free word in the window)', la))
        print('pass', it, ': conflicts', len(conflicts), 'scratch words moved', fixed)
        if not fixed: break
    print('lui groups still conflicting:', len(conflicts))
    for la, res, news in conflicts: print('   conflict at %X:' % la, [('%X' % b, kind, '%X' % A, '%X' % r) for (b, kind, A), r in zip(res, news)][:14])
    print('translation problems:', dict(bad))
    same = ok_ = diff = 0; dl = []
    for a in sorted(hook_words):
        na = newaddr[a]
        if na is None: continue
        o = ntsc.w(a); p_ = pal.w(na)
        if o is None or p_ is None: continue
        if o == p_: same += 1
        elif mk(o) == mk(p_) or (o & 0xFFFF0000) == (p_ & 0xFFFF0000): ok_ += 1
        else: diff += 1; dl.append(a)
    print('hook words: identical original in PAL', same, '| equal modulo immediate', ok_, '| DIFFERENT', diff, ['%X' % a for a in dl[:20]])
    zero_bad = [a for a in hook_words if ntsc.w(a) == 0 and pal.w(newaddr[a] or 0) not in (0, None)]
    print('hook words that were zero in NTSC but not in PAL:', len(zero_bad), ['%X' % a for a in zero_bad[:10]])
    clash = [a for a in cave_words if newaddr[a] is not None and (pal.w(newaddr[a]) or 0) != 0]
    print('cave words landing on non-zero PAL memory:', len(clash), ['%X->%X' % (a, newaddr[a]) for a in clash[:10]])
    coll = collections.Counter(newaddr[a] for a in W if newaddr[a] is not None)
    print('new address collisions:', sum(1 for c in coll.values() if c > 1))
    # scratch words that map onto PAL game words
    sc_bad = []
    for A in sorted(scratch | set(over)):
        r = T(A, 'scratch')
        if r is not None and pal.w(r) not in (0, None): sc_bad.append((A, r))
    print('scratch words landing on non-zero PAL words:', len(sc_bad), ['%X->%X' % x for x in sc_bad[:10]])
    pickle.dump((W, SH, new, newaddr, code, hook_words, cave, bmap, smap, notes, over), open(os.path.join(os.environ.get('TEMP', '.'), 'pal_port_state.pkl'), 'wb'))
    for why, A in notes[:25]: print('  note', why, '%X' % A)

    # PAL runs at 50 Hz: some game float constants are 1.2x the NTSC ones. A patch that replaces such a constant is scaled by the same ratio.
    scaled = []
    def f32(x): return struct.unpack('<f', struct.pack('<I', x))[0]
    def b32(f): return struct.unpack('<I', struct.pack('<f', f))[0]
    for a in sorted(hook_words):
        if not (DATA_LO <= a < DATA_HI): continue
        o_ = ntsc.w(a); p_ = pal.w(newaddr[a])
        if o_ in (None, 0) or p_ in (None, 0) or o_ == p_: continue
        fo, fp, fn = f32(o_), f32(p_), f32(W[a])
        if fo == fo and fp == fp and fo != 0 and 1.1 <= fp / fo <= 1.3:
            new[a] = b32(fn * fp / fo); scaled.append(a)
    print('float data patches scaled by the 50 Hz ratio:', ['%X' % a for a in scaled])
    # verification of the translated jumps / data references into the game
    jbad = 0; jtot = 0
    for a in sorted(code):
        w = W[a]
        if (w >> 26) in (2, 3):
            tg = decode_targets(W, a, w)
            if TEXT_LO <= tg < TEXT_HI and not block_of(tg):
                jtot += 1; r = (new[a] & 0x3FFFFFF) << 2
                if any(mk(ntsc.w(tg + 4 * k)) != mk(pal.w(r + 4 * k)) for k in range(4)): jbad += 1; notes.append(('jump target differs', a))
    print('jumps into game code: %d, target start differs in PAL: %d' % (jtot, jbad))
    # ---- write the pnach
    if '--write' in sys.argv:
        out = []
        for l in lines:
            m = re.match(r'patch=1,EE,([0-9A-Fa-f]{8}),(word|short),([0-9A-Fa-f]+)', l)
            if not m: out.append(l); continue
            a = int(m[1], 16)
            if m[2] == 'word': out.append('patch=1,EE,%08X,word,%08X' % (newaddr[a], new[a]))
            else:
                r = M.data(a) if DATA_LO <= a < DATA_HI else None
                out.append('patch=1,EE,%08X,short,%s' % (r if r is not None else a, m[3]))
        if out and out[0].startswith('gametitle='): out[0] = 'gametitle=Drakengard (SLES-52322) CRC 79585776 - PAL port of the NTSC-U overhaul'
        out.insert(1, '// PAL port (automatic, src/pal_port.py): the comments below describe the NTSC-U addresses; the patch lines are translated.')
        open(PNACH_OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(out))
        print('written', PNACH_OUT)


if __name__ == '__main__':
    main()

