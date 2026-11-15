"""Tiny MIPS (R5900 subset) assembler + interpreter used to verify hand-written patch caves."""
import struct, math

REGS = ["zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
        "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"]
R = {n: i for i, n in enumerate(REGS)}

def r(n):
    return R[n]

def f(n):
    assert n.startswith('f'); return int(n[1:])

def imm16(v):
    return v & 0xFFFF

class Asm:
    def __init__(self, base):
        self.base = base
        self.items = []   # (kind, data)
        self.labels = {}

    def label(self, name):
        self.labels[name] = self.base + 4 * len(self.items)

    def emit(self, *a):
        self.items.append(a)

    def addr(self):
        return self.base + 4 * len(self.items)

    # generic encoders ------------------------------------------------
    def assemble(self):
        out = []
        for idx, it in enumerate(self.items):
            pc = self.base + 4 * idx
            out.append(self.enc(it, pc))
        return out

    def target(self, t):
        return self.labels[t] if isinstance(t, str) else t

    def enc(self, it, pc):
        op = it[0]
        a = it[1:]
        if op == 'nop': return 0
        # I-type ALU
        if op in ('addiu', 'andi', 'ori', 'sltiu', 'slti', 'xori'):
            code = {'addiu': 9, 'andi': 12, 'ori': 13, 'sltiu': 11, 'slti': 10, 'xori': 14}[op]
            return (code << 26) | (r(a[1]) << 21) | (r(a[0]) << 16) | imm16(a[2])
        if op == 'lui':
            return (15 << 26) | (r(a[0]) << 16) | imm16(a[1])
        if op in ('lw', 'sw', 'lh', 'lhu', 'sh', 'lbu', 'sb', 'lb', 'ld', 'lq', 'sq'):
            code = {'lw': 0x23, 'sw': 0x2B, 'lh': 0x21, 'lhu': 0x25, 'sh': 0x29, 'lbu': 0x24, 'sb': 0x28, 'lb': 0x20, 'ld': 0x37, 'lq': 0x1E, 'sq': 0x1F}[op]
            return (code << 26) | (r(a[2]) << 21) | (r(a[0]) << 16) | imm16(a[1])
        if op in ('lwc1', 'swc1'):
            code = {'lwc1': 0x31, 'swc1': 0x39}[op]
            return (code << 26) | (r(a[2]) << 21) | (f(a[0]) << 16) | imm16(a[1])
        # R-type
        if op in ('or', 'and', 'addu', 'subu', 'nor', 'xor', 'sltu', 'slt', 'daddu'):
            fn = {'or': 0x25, 'and': 0x24, 'addu': 0x21, 'subu': 0x23, 'nor': 0x27, 'xor': 0x26, 'sltu': 0x2B, 'slt': 0x2A, 'daddu': 0x2D}[op]
            return (r(a[1]) << 21) | (r(a[2]) << 16) | (r(a[0]) << 11) | fn
        if op in ('sll', 'srl', 'sra'):
            fn = {'sll': 0, 'srl': 2, 'sra': 3}[op]
            return (r(a[1]) << 16) | (r(a[0]) << 11) | (a[2] << 6) | fn
        if op == 'mult':
            return (r(a[0]) << 21) | (r(a[1]) << 16) | 0x18
        if op == 'mfc0':
            return (0x10 << 26) | (r(a[0]) << 16) | (a[1] << 11)
        if op == 'mflo':
            return (r(a[0]) << 11) | 0x12
        if op == 'jr':
            return (r(a[0]) << 21) | 8
        if op in ('j', 'jal'):
            t = self.target(a[0])
            return ((2 if op == 'j' else 3) << 26) | ((t >> 2) & 0x3FFFFFF)
        if op in ('beq', 'bne'):
            t = self.target(a[2])
            off = (t - (pc + 4)) >> 2
            return ((4 if op == 'beq' else 5) << 26) | (r(a[0]) << 21) | (r(a[1]) << 16) | imm16(off)
        if op in ('bc1t', 'bc1f'):
            t = self.target(a[0])
            off = (t - (pc + 4)) >> 2
            return (0x11 << 26) | (8 << 21) | ((1 if op == 'bc1t' else 0) << 16) | imm16(off)
        # COP1
        if op == 'mtc1':
            return (0x11 << 26) | (4 << 21) | (r(a[0]) << 16) | (f(a[1]) << 11)
        if op == 'mfc1':
            return (0x11 << 26) | (0 << 21) | (r(a[0]) << 16) | (f(a[1]) << 11)
        if op == 'cvt.w.s':
            return (0x11 << 26) | (0x10 << 21) | (f(a[1]) << 11) | (f(a[0]) << 6) | 0x24
        if op == 'cvt.s.w':
            return (0x11 << 26) | (0x14 << 21) | (f(a[1]) << 11) | (f(a[0]) << 6) | 0x20
        S = {'add.s': 0, 'sub.s': 1, 'mul.s': 2, 'div.s': 3, 'sqrt.s': 4, 'abs.s': 5, 'mov.s': 6, 'neg.s': 7, 'rsqrt.s': 0x16}
        if op in S:
            fn = S[op]
            if op == 'sqrt.s':
                return (0x11 << 26) | (0x10 << 21) | (f(a[1]) << 16) | (0 << 11) | (f(a[0]) << 6) | fn   # R5900: the source is in ft, fs is 0
            if op in ('abs.s', 'mov.s', 'neg.s'):
                return (0x11 << 26) | (0x10 << 21) | (0 << 16) | (f(a[1]) << 11) | (f(a[0]) << 6) | fn
            return (0x11 << 26) | (0x10 << 21) | (f(a[2]) << 16) | (f(a[1]) << 11) | (f(a[0]) << 6) | fn
        if op == 'c.olt.s':
            return (0x11 << 26) | (0x10 << 21) | (f(a[1]) << 16) | (f(a[0]) << 11) | 0x34
        if op == 'c.le.s':
            return (0x11 << 26) | (0x10 << 21) | (f(a[1]) << 16) | (f(a[0]) << 11) | 0x3E
        raise ValueError('unknown op ' + op)

# ---------------------------------------------------------------- interpreter
class CPU:
    def __init__(self):
        self.mem = {}
        self.r = [0] * 32
        self.f = [0.0] * 32
        self.cc = False

    def rb(self, a): return self.mem.get(a, 0)
    def wb(self, a, v): self.mem[a] = v & 0xFF
    def rw(self, a): return sum(self.rb(a + i) << (8 * i) for i in range(4))
    def ww(self, a, v):
        for i in range(4): self.wb(a + i, (v >> (8 * i)) & 0xFF)
    def rh(self, a): return self.rb(a) | (self.rb(a + 1) << 8)
    def wh(self, a, v): self.wb(a, v); self.wb(a + 1, v >> 8)
    def rf(self, a): return struct.unpack('<f', struct.pack('<I', self.rw(a)))[0]
    def wf(self, a, v): self.ww(a, struct.unpack('<I', struct.pack('<f', v))[0])
    def s32(self, v): v &= 0xFFFFFFFF; return v - (1 << 32) if v & 0x80000000 else v

    def load_words(self, base, words):
        for i, w in enumerate(words): self.ww(base + 4 * i, w)

    def run(self, pc, stop_pc, maxsteps=5000):
        steps = 0
        delay = None
        npc = pc
        while pc != stop_pc and steps < maxsteps:
            steps += 1
            w = self.rw(pc)
            self.exec1(w, pc)
            # handle delay slot model: self.branch set by exec1 -> (target)
            if self.branch is not None:
                tgt = self.branch; self.branch = None
                # execute delay slot
                wd = self.rw(pc + 4)
                self.exec1(wd, pc + 4)
                self.branch = None
                pc = tgt
            else:
                pc += 4
        return steps, pc

    branch = None

    def setr(self, i, v):
        if i: self.r[i] = v & 0xFFFFFFFF

    def exec1(self, w, pc):
        op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31; rd = (w >> 11) & 31; sh = (w >> 6) & 31
        imm = w & 0xFFFF; simm = imm - 0x10000 if imm & 0x8000 else imm; fn = w & 63
        R_ = self.r
        if w == 0: return
        if op == 0:
            if fn == 0: self.setr(rd, R_[rt] << sh)
            elif fn == 2: self.setr(rd, (R_[rt] & 0xFFFFFFFF) >> sh)
            elif fn == 3: self.setr(rd, self.s32(R_[rt]) >> sh)
            elif fn == 8: self.branch = R_[rs]
            elif fn == 0x18: self.lo = (self.s32(R_[rs]) * self.s32(R_[rt])) & 0xFFFFFFFF
            elif fn == 0x12: self.setr(rd, self.lo)
            elif fn == 0x21 or fn == 0x2D: self.setr(rd, R_[rs] + R_[rt])
            elif fn == 0x23: self.setr(rd, R_[rs] - R_[rt])
            elif fn == 0x24: self.setr(rd, R_[rs] & R_[rt])
            elif fn == 0x25: self.setr(rd, R_[rs] | R_[rt])
            elif fn == 0x26: self.setr(rd, R_[rs] ^ R_[rt])
            elif fn == 0x27: self.setr(rd, ~(R_[rs] | R_[rt]))
            elif fn == 0x2A: self.setr(rd, 1 if self.s32(R_[rs]) < self.s32(R_[rt]) else 0)
            elif fn == 0x2B: self.setr(rd, 1 if (R_[rs] & 0xFFFFFFFF) < (R_[rt] & 0xFFFFFFFF) else 0)
            else: raise ValueError('special %x' % fn)
        elif op == 0x10:
            if rs == 0: self.setr(rt, 0x12345678)
            else: raise ValueError('cop0')
        elif op == 0x10:
            if rs == 0: self.setr(rt, 0x12345678)
            else: raise ValueError('cop0')
        elif op == 2: self.branch = ((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
        elif op == 3: self.branch = ((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2); R_[31] = pc + 8
        elif op == 4:
            if R_[rs] == R_[rt]: self.branch = pc + 4 + (simm << 2)
        elif op == 5:
            if R_[rs] != R_[rt]: self.branch = pc + 4 + (simm << 2)
        elif op == 9: self.setr(rt, R_[rs] + simm)
        elif op == 10: self.setr(rt, 1 if self.s32(R_[rs]) < simm else 0)
        elif op == 11: self.setr(rt, 1 if (R_[rs] & 0xFFFFFFFF) < (simm & 0xFFFFFFFF) else 0)
        elif op == 12: self.setr(rt, R_[rs] & imm)
        elif op == 13: self.setr(rt, R_[rs] | imm)
        elif op == 14: self.setr(rt, R_[rs] ^ imm)
        elif op == 15: self.setr(rt, imm << 16)
        elif op == 0x37: self.setr(rt, self.rw(R_[rs] + simm))
        elif op == 0x23: self.setr(rt, self.rw(R_[rs] + simm))
        elif op == 0x21:
            v = self.rh(R_[rs] + simm); self.setr(rt, v - 0x10000 if v & 0x8000 else v)
        elif op == 0x25: self.setr(rt, self.rh(R_[rs] + simm))
        elif op == 0x24: self.setr(rt, self.rb(R_[rs] + simm))
        elif op == 0x2B: self.ww(R_[rs] + simm, R_[rt])
        elif op == 0x29: self.wh(R_[rs] + simm, R_[rt])
        elif op == 0x28: self.wb(R_[rs] + simm, R_[rt])
        elif op == 0x31: self.f[rt] = self.rf(R_[rs] + simm)
        elif op == 0x39: self.wf(R_[rs] + simm, self.f[rt])
        elif op == 0x11:
            if rs == 4: self.f[rd] = struct.unpack('<f', struct.pack('<I', R_[rt] & 0xFFFFFFFF))[0]
            elif rs == 0: self.setr(rt, struct.unpack('<I', struct.pack('<f', self.f[rd]))[0])
            elif rs == 8:
                taken = (self.cc == bool(rt & 1))
                if taken: self.branch = pc + 4 + (simm << 2)
            elif rs == 0x14:
                v = self.s32(struct.unpack('<I', struct.pack('<f', self.f[rd]))[0]) if False else None
                # cvt.s.w: source register holds an integer bit pattern; we model int in f via raw bits
                raw = struct.unpack('<I', struct.pack('<f', self.f[rd]))[0] if not isinstance(self.f[rd], int) else self.f[rd]
                self.f[sh] = float(self.s32(raw))
            elif rs == 0x10:
                ft = rt; fs = rd; fd = sh
                if fn == 0: self.f[fd] = self.f[fs] + self.f[ft]
                elif fn == 1: self.f[fd] = self.f[fs] - self.f[ft]
                elif fn == 2: self.f[fd] = self.f[fs] * self.f[ft]
                elif fn == 3: self.f[fd] = self.f[fs] / self.f[ft]
                elif fn == 4: self.f[fd] = math.sqrt(self.f[ft])
                elif fn == 5: self.f[fd] = abs(self.f[fs])
                elif fn == 6: self.f[fd] = self.f[fs]
                elif fn == 7: self.f[fd] = -self.f[fs]
                elif fn == 0x16: self.f[fd] = self.f[fs] / math.sqrt(self.f[ft])
                elif fn == 0x24: self.f[fd] = struct.unpack('<f', struct.pack('<i', int(math.trunc(self.f[fs]))))[0]
                elif fn == 0x34: self.cc = self.f[fs] < self.f[ft]
                elif fn == 0x3E: self.cc = self.f[fs] <= self.f[ft]
                else: raise ValueError('cop1 fn %x' % fn)
            else: raise ValueError('cop1 rs %x' % rs)
        else: raise ValueError('op %x' % op)


