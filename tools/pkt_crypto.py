"""Read and write Cisco Packet Tracer .pkt/.pka files (PT 7+ format), pure Python.

File format (as documented by the open-source pka2xml project):
  file  = obfuscate1( EAX<Twofish>(key=0x89*16, iv=0x10*16).encrypt( obfuscate2( size_be32 + zlib(xml) ) ) + tag )
Usage:
  python tools/pkt_crypto.py decode in.pkt out.xml
  python tools/pkt_crypto.py encode in.xml out.pkt
"""
import sys
import zlib

# ---------------------------------------------------------------- Twofish (encrypt only, 128-bit key)
_Q0T = ([8, 1, 7, 13, 6, 15, 3, 2, 0, 11, 5, 9, 14, 12, 10, 4],
        [14, 12, 11, 8, 1, 2, 3, 5, 15, 4, 10, 6, 7, 0, 9, 13],
        [11, 10, 5, 14, 6, 13, 9, 0, 12, 8, 15, 3, 2, 4, 7, 1],
        [13, 7, 15, 4, 1, 2, 6, 14, 9, 11, 3, 0, 8, 5, 12, 10])
_Q1T = ([2, 8, 11, 13, 15, 7, 6, 14, 3, 1, 9, 4, 0, 10, 12, 5],
        [1, 14, 2, 11, 4, 12, 3, 7, 6, 13, 10, 5, 15, 9, 0, 8],
        [4, 12, 7, 5, 1, 6, 9, 10, 0, 14, 13, 8, 2, 11, 3, 15],
        [11, 9, 5, 1, 12, 3, 13, 14, 6, 4, 7, 15, 2, 0, 8, 10])


def _ror4(x, n):
    return ((x >> n) | (x << (4 - n))) & 15


def _mkq(t):
    q = []
    for x in range(256):
        a0, b0 = x >> 4, x & 15
        a1 = a0 ^ b0
        b1 = a0 ^ _ror4(b0, 1) ^ ((8 * a0) & 15)
        a2, b2 = t[0][a1], t[1][b1]
        a3 = a2 ^ b2
        b3 = a2 ^ _ror4(b2, 1) ^ ((8 * a2) & 15)
        a4, b4 = t[2][a3], t[3][b3]
        q.append(16 * b4 + a4)
    return q


Q0, Q1 = _mkq(_Q0T), _mkq(_Q1T)
M32 = 0xFFFFFFFF


def _gfmul(a, b, poly):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        if a & 0x100:
            a ^= poly
        b >>= 1
    return r


_MDS = [[0x01, 0xEF, 0x5B, 0x5B], [0x5B, 0xEF, 0xEF, 0x01],
        [0xEF, 0x5B, 0x01, 0xEF], [0xEF, 0x01, 0xEF, 0x5B]]
_RS = [[0x01, 0xA4, 0x55, 0x87, 0x5A, 0x58, 0xDB, 0x9E],
       [0xA4, 0x56, 0x82, 0xF3, 0x1E, 0xC6, 0x68, 0xE5],
       [0x02, 0xA1, 0xFC, 0xC1, 0x47, 0xAE, 0x3D, 0x19],
       [0xA4, 0x55, 0x87, 0x5A, 0x58, 0xDB, 0x9E, 0x03]]


def _mds(y):
    out = 0
    for i in range(4):
        v = 0
        for j in range(4):
            v ^= _gfmul(_MDS[i][j], y[j], 0x169)
        out |= v << (8 * i)
    return out


def _bytes(w):
    return [(w >> (8 * i)) & 0xFF for i in range(4)]


def _h_bytes(x, L0, L1):
    l0, l1 = _bytes(L0), _bytes(L1)
    return [Q1[Q0[Q0[x[0]] ^ l1[0]] ^ l0[0]],
            Q0[Q0[Q1[x[1]] ^ l1[1]] ^ l0[1]],
            Q1[Q1[Q0[x[2]] ^ l1[2]] ^ l0[2]],
            Q0[Q1[Q1[x[3]] ^ l1[3]] ^ l0[3]]]


def _rol(x, n):
    return ((x << n) | (x >> (32 - n))) & M32


def _ror(x, n):
    return ((x >> n) | (x << (32 - n))) & M32


class Twofish128:
    def __init__(self, key):
        assert len(key) == 16
        M = [int.from_bytes(key[4 * i:4 * i + 4], 'little') for i in range(4)]
        S = []
        for i in range(2):
            m = key[8 * i:8 * i + 8]
            v = 0
            for r in range(4):
                b = 0
                for c in range(8):
                    b ^= _gfmul(_RS[r][c], m[c], 0x14D)
                v |= b << (8 * r)
            S.append(v)
        rho = 0x01010101
        K = []
        for i in range(20):
            A = _mds(_h_bytes(_bytes((2 * i * rho) & M32), M[0], M[2]))
            B = _rol(_mds(_h_bytes(_bytes(((2 * i + 1) * rho) & M32), M[1], M[3])), 8)
            K.append((A + B) & M32)
            K.append(_rol((A + 2 * B) & M32, 9))
        self.K = K
        # keyed g() as 4 lookup tables: g(X) = T0[x0]^T1[x1]^T2[x2]^T3[x3]
        L0, L1 = S[1], S[0]
        self.T = [[0] * 256 for _ in range(4)]
        for x in range(256):
            for pos in range(4):
                xb = [0, 0, 0, 0]
                xb[pos] = x
                y = _h_bytes(xb, L0, L1)
                yy = [0, 0, 0, 0]
                yy[pos] = y[pos]
                self.T[pos][x] = _mds(yy)

    def _g(self, x):
        T = self.T
        return T[0][x & 0xFF] ^ T[1][(x >> 8) & 0xFF] ^ T[2][(x >> 16) & 0xFF] ^ T[3][x >> 24]

    def encrypt_block(self, blk):
        K = self.K
        R = [int.from_bytes(blk[4 * i:4 * i + 4], 'little') ^ K[i] for i in range(4)]
        g = self._g
        for r in range(16):
            t0 = g(R[0])
            t1 = g(_rol(R[1], 8))
            f0 = (t0 + t1 + K[2 * r + 8]) & M32
            f1 = (t0 + 2 * t1 + K[2 * r + 9]) & M32
            n2 = _ror(R[2] ^ f0, 1)
            n3 = _rol(R[3], 1) ^ f1
            R = [n2, n3, R[0], R[1]]
        C = [R[2] ^ K[4], R[3] ^ K[5], R[0] ^ K[6], R[1] ^ K[7]]
        return b''.join(c.to_bytes(4, 'little') for c in C)


# ---------------------------------------------------------------- EAX mode
def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def _dbl(b):
    n = int.from_bytes(b, 'big') << 1
    if n >> 128:
        n = (n & ((1 << 128) - 1)) ^ 0x87
    return n.to_bytes(16, 'big')


def _cmac(E, msg):
    L = E(bytes(16))
    k1 = _dbl(L)
    k2 = _dbl(k1)
    blocks = [msg[i:i + 16] for i in range(0, len(msg), 16)] or [b'']
    last = blocks[-1]
    if len(last) == 16:
        last = _xor(last, k1)
    else:
        last = _xor(last + b'\x80' + bytes(15 - len(last)), k2)
    x = bytes(16)
    for b in blocks[:-1]:
        x = E(_xor(x, b))
    return E(_xor(x, last))


def _ctr(E, n0, data):
    c = int.from_bytes(n0, 'big')
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = E(c.to_bytes(16, 'big'))
        out += _xor(data[i:i + 16], ks)
        c = (c + 1) & ((1 << 128) - 1)
    return bytes(out)


def eax_encrypt(cipher, nonce, data):
    E = cipher.encrypt_block
    n = _cmac(E, bytes(15) + b'\x00' + nonce)
    h = _cmac(E, bytes(15) + b'\x01')
    c = _ctr(E, n, data)
    t = _cmac(E, bytes(15) + b'\x02' + c)
    return c + _xor(_xor(n, h), t)


def eax_decrypt(cipher, nonce, data):
    E = cipher.encrypt_block
    c, tag = data[:-16], data[-16:]
    n = _cmac(E, bytes(15) + b'\x00' + nonce)
    h = _cmac(E, bytes(15) + b'\x01')
    t = _cmac(E, bytes(15) + b'\x02' + c)
    if _xor(_xor(n, h), t) != tag:
        raise ValueError('EAX tag mismatch')
    return _ctr(E, n, c)


# ---------------------------------------------------------------- Packet Tracer layers
KEY, IV = bytes([137] * 16), bytes([16] * 16)


def _ob2(b):
    n = len(b)
    return bytes(x ^ ((n - i) & 0xFF) for i, x in enumerate(b))


def decode(raw):
    n = len(raw)
    stage1 = bytes(raw[n - 1 - i] ^ ((n - i * n) & 0xFF) for i in range(n))
    plain = _ob2(eax_decrypt(Twofish128(KEY), IV, stage1))
    size = int.from_bytes(plain[:4], 'big')
    xml = zlib.decompress(plain[4:])
    assert len(xml) == size
    return xml


def encode(xml):
    comp = len(xml).to_bytes(4, 'big') + zlib.compress(xml, 9)
    enc = eax_encrypt(Twofish128(KEY), IV, _ob2(comp))
    n = len(enc)
    out = bytearray(n)
    for i in range(n):
        out[n - 1 - i] = enc[i] ^ ((n - i * n) & 0xFF)
    return bytes(out)


def _selftest():
    ct = Twofish128(bytes(16)).encrypt_block(bytes(16))
    assert ct.hex().upper() == '9F589F5CF6122C32B6BFEC2F2AE8C35A', ct.hex()


if __name__ == '__main__':
    _selftest()
    if len(sys.argv) == 4 and sys.argv[1] in ('decode', 'encode'):
        data = open(sys.argv[2], 'rb').read()
        out = decode(data) if sys.argv[1] == 'decode' else encode(data)
        open(sys.argv[3], 'wb').write(out)
        print(sys.argv[1], 'ok:', len(data), '->', len(out), 'bytes')
    else:
        print('self-test ok')
