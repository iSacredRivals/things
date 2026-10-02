"""Luraph v14.8 payload extraction: [==[LPH...]==] long bracket -> ASCII85 ->
LE uint32 buffer -> string constants. Validates against the known dump."""
import re
import sys


def find_lph_payload(source):
    """[(equals_count, payload_bytes)] of every [==[LPH...]==] bracket."""
    out = []
    for m in re.finditer(r'\[(=*)\[LPH', source):
        eq = m.group(1)
        end = ']' + eq + ']'
        e = source.find(end, m.end())
        if e < 0:
            continue
        raw = source[m.end():e]
        out.append((len(eq), raw))
    return out


def decode_ascii85_lph(raw):
    """Luraph's ASCII85: 'z' expands to 5 zero bytes; each 5-char group is a
    big-endian base-85 number written as a little-endian uint32."""
    expanded = raw.replace('z', '!!!!!')
    expanded = ''.join(expanded.split())
    rem = len(expanded) % 5
    if rem:
        expanded += 'u' * (5 - rem)
    buf = bytearray()
    for off in range(0, len(expanded), 5):
        word = 0
        for ch in expanded[off:off + 5]:
            word = word * 85 + max(0, min(84, ord(ch) - 33))
        buf += (word & 0xFFFFFFFF).to_bytes(4, 'little')
    return bytes(buf)


def extract_strings(buf, min_len=2, max_len=200):
    """Scan the decoded buffer for printable strings (Luraph stores proto
    string constants inline: length-prefixed, mixed with opcode/operand data).
    Returns them in buffer order."""
    out, i, n = [], 0, len(buf)
    while i < n:
        j = i
        while j < n and 32 <= buf[j] <= 126:
            j += 1
        if j - i >= min_len:
            s = buf[i:j].decode('latin-1')
            out.append((i, s))
        i = j + 1
    # long strings only; the localization table is the bulk
    return [(off, s) for off, s in out if min_len <= len(s) <= max_len]


if __name__ == '__main__':
    src = open(sys.argv[1], 'rb').read().decode('latin-1')
    brackets = find_lph_payload(src)
    print('LPH brackets:', [(eq, len(raw)) for eq, raw in brackets])
    for eq, raw in brackets:
        buf = decode_ascii85_lph(raw)
        print('decoded buffer: %d bytes' % len(buf))
        open('/tmp/v148_payload.bin', 'wb').write(buf)
        strs = extract_strings(buf)
        print('printable runs (2..200):', len(strs))
        total = sum(len(s) for _, s in strs)
        print('total string bytes:', total)
        # compare with the suite's known-good constants dump
        known = open('/home/z/my-project/v148_suite/replit_original_project/luraph-constants (1).lua',
                     encoding='utf-8', errors='ignore').read()
        hits, misses = 0, []
        for off, s in strs[:2000]:
            if len(s) >= 4:
                if s in known:
                    hits += 1
                else:
                    misses.append((off, s[:60]))
        print('sample 2000: %d in known dump, %d not' % (hits, len(misses)))
        for off, s in misses[:10]:
            print('  MISS', off, repr(s))
        # show a slice of the strings
        shown = 0
        for off, s in strs:
            if 20 <= len(s) <= 90:
                print('  %7d %r' % (off, s))
                shown += 1
                if shown >= 25:
                    break
