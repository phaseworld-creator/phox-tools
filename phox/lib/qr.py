GF_POLY = 0x11D

_gf_exp = [0] * 512
_gf_log = [0] * 256

_x = 1
for _i in range(255):
    _gf_exp[_i] = _x
    _gf_log[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= GF_POLY
for _i in range(255, 512):
    _gf_exp[_i] = _gf_exp[_i - 255]


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _gf_exp[_gf_log[a] + _gf_log[b]]


def gf_pow(x, power):
    return _gf_exp[(_gf_log[x] * power) % 255]

def _rs_generator_poly(nsym):
    g = [1]
    for i in range(nsym):
        new_g = [0] * (len(g) + 1)
        for j in range(len(g)):
            new_g[j] ^= g[j]
            new_g[j + 1] ^= gf_mul(g[j], gf_pow(2, i))
        g = new_g
    return g


def rs_encode(data, nsym):
    gen = _rs_generator_poly(nsym)
    res = list(data) + [0] * nsym
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(1, len(gen)):
                res[i + j] ^= gf_mul(gen[j], coef)
    return res[len(data):]

_VERSION_TABLE = {
    1:  (26,  10, 1),
    2:  (44,  16, 1),
    3:  (70,  26, 1),
    4:  (100, 18, 2),
    5:  (134, 24, 2),
    6:  (172, 16, 4),
    7:  (196, 18, 4),
    8:  (242, 22, 4),
    9:  (292, 22, 5),
    10: (346, 26, 6),
    11: (404, 30, 8),
    12: (466, 22, 10),
    13: (532, 22, 12),
    14: (581, 24, 14),
    15: (655, 24, 16),
    16: (733, 28, 18),
    17: (815, 28, 20),
    18: (901, 26, 22),
    19: (991, 26, 24),
    20: (1085, 26, 26),
}

_ALIGNMENT = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46],
    10: [6, 28, 50], 11: [6, 30, 54], 12: [6, 32, 58], 13: [6, 34, 62],
    14: [6, 26, 46, 66], 15: [6, 26, 48, 70], 16: [6, 26, 50, 74],
    17: [6, 30, 54, 78], 18: [6, 30, 56, 82], 19: [6, 30, 58, 86],
    20: [6, 34, 62, 90],
}


def _get_version(data_len):
    for v in range(1, 21):
        total, ec_per, num_blocks = _VERSION_TABLE[v]
        data_total = total - ec_per * num_blocks
        overhead = 4 + (8 if v <= 9 else 16)
        if data_len <= (data_total * 8 - overhead) // 8:
            return v
    raise ValueError("Data too long for QR code versions 1-20")


def _encode_data(text, version):
    data = text.encode("utf-8")
    bits = []

    bits.extend([0, 1, 0, 0])

    count_len = 8 if version <= 9 else 16
    for i in range(count_len - 1, -1, -1):
        bits.append((len(data) >> i) & 1)

    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)

    total_bits = _VERSION_TABLE[version][0] * 8
    bits.extend([0] * min(4, total_bits - len(bits)))

    while len(bits) % 8 != 0:
        bits.append(0)

    pad_vals = [0xEC, 0x11]
    pad_i = 0
    while len(bits) < total_bits:
        pb = pad_vals[pad_i % 2]
        for i in range(7, -1, -1):
            bits.append((pb >> i) & 1)
        pad_i += 1

    codewords = []
    for i in range(0, total_bits, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        codewords.append(byte)

    return codewords


def _build_codewords(data_cw, version):
    total, ec_per, num_blocks = _VERSION_TABLE[version]
    data_per = total // num_blocks
    extra = total % num_blocks

    blocks = []
    offset = 0
    for i in range(num_blocks):
        sz = data_per + (1 if i < extra else 0)
        blocks.append(data_cw[offset:offset + sz])
        offset += sz

    ec_blocks = [rs_encode(b, ec_per) for b in blocks]

    result = []
    max_data = max(len(b) for b in blocks)
    for i in range(max_data):
        for b in blocks:
            if i < len(b):
                result.append(b[i])

    for i in range(ec_per):
        for b in ec_blocks:
            if i < len(b):
                result.append(b[i])

    return result

class _Matrix:
    def __init__(self, version):
        self.version = version
        self.size = version * 4 + 17
        self.modules = [[None] * self.size for _ in range(self.size)]
        self.is_function = [[False] * self.size for _ in range(self.size)]

    def set(self, r, c, val, is_func=False):
        if 0 <= r < self.size and 0 <= c < self.size:
            self.modules[r][c] = val
            if is_func:
                self.is_function[r][c] = True

    def get(self, r, c):
        if 0 <= r < self.size and 0 <= c < self.size:
            return self.modules[r][c]
        return None

    def place_function_patterns(self):
        self._place_finders()
        self._place_timing()
        self._place_alignment()
        self._place_dark_module()
        self._reserve_format_area()

    def _place_finders(self):
        positions = [(0, 0), (0, self.size - 7), (self.size - 7, 0)]
        for pr, pc in positions:
            for dr in range(-1, 8):
                for dc in range(-1, 8):
                    r, c = pr + dr, pc + dc
                    if r < 0 or r >= self.size or c < 0 or c >= self.size:
                        continue
                    is_border = dr in (0, 6) or dc in (0, 6)
                    is_center = 2 <= dr <= 4 and 2 <= dc <= 4
                    val = is_center or is_border
                    self.set(r, c, val, is_func=True)

    def _place_timing(self):
        for i in range(8, self.size - 8):
            val = (i % 2 == 0)
            self.set(6, i, val, is_func=True)
            self.set(i, 6, val, is_func=True)

    def _place_alignment(self):
        if self.version < 2:
            return
        positions = _ALIGNMENT[self.version]
        for r in positions:
            for c in positions:
                if self.is_function[r][c]:
                    continue
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        val = max(abs(dr), abs(dc)) != 1
                        self.set(r + dr, c + dc, val, is_func=True)

    def _place_dark_module(self):
        self.set(self.size - 8, 8, True, is_func=True)

    def _reserve_format_area(self):
        for i in range(9):
            self.is_function[8][i] = True
            self.is_function[i][8] = True
        for i in range(8):
            self.is_function[8][self.size - 1 - i] = True
        for i in range(7):
            self.is_function[self.size - 1 - i][8] = True

    def place_data_bits(self, codewords):
        bits = []
        for cw in codewords:
            for i in range(7, -1, -1):
                bits.append((cw >> i) & 1)

        idx = 0
        upward = True

        for right in range(self.size - 1, 0, -2):
            if right == 6:
                right -= 1
            for vert in range(self.size):
                row = (self.size - 1 - vert) if upward else vert
                for j in range(2):
                    col = right - j
                    if col < 0:
                        continue
                    if self.is_function[row][col]:
                        continue
                    if idx < len(bits):
                        self.modules[row][col] = bool(bits[idx])
                    else:
                        self.modules[row][col] = False
                    idx += 1
            upward = not upward

    def apply_mask(self, mask_num):
        for r in range(self.size):
            for c in range(self.size):
                if self.is_function[r][c]:
                    continue
                if self._mask_fn(mask_num, r, c):
                    self.modules[r][c] = not self.modules[r][c]

    def _mask_fn(self, mask_num, r, c):
        if mask_num == 0: return (r + c) % 2 == 0
        if mask_num == 1: return r % 2 == 0
        if mask_num == 2: return c % 3 == 0
        if mask_num == 3: return (r + c) % 3 == 0
        if mask_num == 4: return (r // 2 + c // 3) % 2 == 0
        if mask_num == 5: return (r * c) % 2 + (r * c) % 3 == 0
        if mask_num == 6: return ((r * c) % 2 + (r * c) % 3) % 2 == 0
        return ((r + c) % 2 + (r * c) % 3) % 2 == 0

    def place_format_info(self, mask_num):
        FORMAT_TABLE = [
            0x5412, 0x5125, 0x5E7C, 0x5B4B, 0x45F9, 0x40CE, 0x4F97, 0x4AA0,
            0x77C4, 0x72F3, 0x7DAA, 0x789D, 0x662F, 0x6318, 0x6C41, 0x6976,
            0x1689, 0x13BE, 0x1CE7, 0x19D0, 0x0762, 0x0255, 0x0D0C, 0x083B,
            0x355F, 0x3068, 0x3F31, 0x3A06, 0x24B4, 0x2183, 0x2EDA, 0x2BED,
        ]
        bits = FORMAT_TABLE[mask_num]

        top_positions = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
        ]
        for i, (r, c) in enumerate(top_positions):
            self.modules[r][c] = bool((bits >> (14 - i)) & 1)

        bottom_positions = [
            (self.size - 1, 8), (self.size - 2, 8), (self.size - 3, 8),
            (self.size - 4, 8), (self.size - 5, 8), (self.size - 6, 8),
            (self.size - 7, 8),
            (8, self.size - 8), (8, self.size - 7), (8, self.size - 6),
            (8, self.size - 5), (8, self.size - 4), (8, self.size - 3),
            (8, self.size - 2), (8, self.size - 1),
        ]
        for i, (r, c) in enumerate(bottom_positions):
            self.modules[r][c] = bool((bits >> (14 - i)) & 1)

    def copy(self):
        m = _Matrix(self.version)
        m.modules = [row[:] for row in self.modules]
        m.is_function = [row[:] for row in self.is_function]
        return m

    def penalty(self):
        p = 0
        for r in range(self.size):
            run = 1
            for c in range(1, self.size):
                if self.modules[r][c] == self.modules[r][c - 1]:
                    run += 1
                else:
                    if run >= 5:
                        p += run - 2
                    run = 1
            if run >= 5:
                p += run - 2

        for c in range(self.size):
            run = 1
            for r in range(1, self.size):
                if self.modules[r][c] == self.modules[r - 1][c]:
                    run += 1
                else:
                    if run >= 5:
                        p += run - 2
                    run = 1
            if run >= 5:
                p += run - 2

        for r in range(self.size - 1):
            for c in range(self.size - 1):
                v = self.modules[r][c]
                if (v == self.modules[r][c + 1] ==
                        self.modules[r + 1][c] == self.modules[r + 1][c + 1]):
                    p += 3

        return p

def generate(text, ec_level="M"):
    version = _get_version(len(text.encode("utf-8")))

    data_cw = _encode_data(text, version)
    all_cw = _build_codewords(data_cw, version)

    base = _Matrix(version)
    base.place_function_patterns()
    base.place_data_bits(all_cw)

    best_mask = 0
    best_penalty = float("inf")
    best_matrix = None

    for mask in range(8):
        m = base.copy()
        m.apply_mask(mask)
        m.place_format_info(mask)
        p = m.penalty()
        if p < best_penalty:
            best_penalty = p
            best_mask = mask
            best_matrix = m

    return best_matrix.modules


def to_text(matrix, quiet=4):
    size = len(matrix)
    border = "\u2588" * (size * 2 + quiet * 2)
    lines = [border] * quiet
    for r in range(size):
        line = "\u2588" * quiet
        for c in range(size):
            line += "\u2588\u2588" if matrix[r][c] else "  "
        line += "\u2588" * quiet
        lines.append(line)
    lines.extend([border] * quiet)
    return "\n".join(lines)


def to_svg(matrix, module_size=10, fill="black", background="white"):
    size = len(matrix)
    quiet = 4
    total = size + quiet * 2
    px = total * module_size

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {px} {px}" width="{px}" height="{px}">'
        f'<rect width="{px}" height="{px}" fill="{background}"/>',
    ]

    for r in range(size):
        for c in range(size):
            if matrix[r][c]:
                x = (c + quiet) * module_size
                y = (r + quiet) * module_size
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{module_size}" '
                    f'height="{module_size}" fill="{fill}"/>'
                )

    parts.append("</svg>")
    return "\n".join(parts)


def to_pbm(matrix, quiet=4):
    size = len(matrix)
    total = size + quiet * 2
    lines = [f"P1 {total} {total}"]
    for _ in range(quiet):
        lines.append("0" * total)
    for r in range(size):
        line = "0" * quiet
        for c in range(size):
            line += "1" if matrix[r][c] else "0"
        line += "0" * quiet
        lines.append(line)
    for _ in range(quiet):
        lines.append("0" * total)
    return "\n".join(lines)
