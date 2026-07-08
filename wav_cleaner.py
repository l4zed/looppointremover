import os
import struct
import tempfile
import shutil

RIFF = b"RIFF"
RF64 = b"RF64"
WAVE = b"WAVE"

FMT = b"fmt "
DATA = b"data"

REMOVE_CHUNKS = {
    b"smpl",
    b"cue ",
    b"inst",
    b"acid",
    b"strc",
}

KEEP_ALWAYS = {
    b"fmt ",
    b"data",
    b"fact",
    b"bext",
    b"iXML",
    b"axml",
    b"JUNK",
    b"PAD ",
    b"FLLR",
    b"PEAK",
    b"DISP",
}


class Chunk:

    __slots__ = (
        "id",
        "size",
        "offset",
        "data",
    )

    def __init__(self, cid, size, offset, data):
        self.id = cid
        self.size = size
        self.offset = offset
        self.data = data


def read_u32(buf, pos):
    return struct.unpack_from("<I", buf, pos)[0]


def write_u32(value):
    return struct.pack("<I", value)


def is_riff(buf):

    if len(buf) < 12:
        return False

    if buf[:4] not in (RIFF, RF64):
        return False

    if buf[8:12] != WAVE:
        return False

    return True


def iter_chunks(buf):

    pos = 12
    end = len(buf)

    while pos + 8 <= end:

        cid = buf[pos:pos + 4]
        size = read_u32(buf, pos + 4)

        data_start = pos + 8
        data_end = data_start + size

        if data_end > end:
            break

        yield Chunk(
            cid,
            size,
            pos,
            buf[data_start:data_end]
        )

        pos = data_end

        if size & 1:
            pos += 1

def parse_list_chunk(chunk):

    if len(chunk.data) < 4:
        return None, []

    list_type = chunk.data[:4]

    items = []

    pos = 4
    end = len(chunk.data)

    while pos + 8 <= end:

        cid = chunk.data[pos:pos + 4]
        size = read_u32(chunk.data, pos + 4)

        start = pos + 8
        stop = start + size

        if stop > end:
            break

        payload = chunk.data[start:stop]

        items.append((cid, payload))

        pos = stop

        if size & 1:
            pos += 1

    return list_type, items


def build_list_chunk(list_type, items):

    out = bytearray()

    out += list_type

    for cid, payload in items:

        out += cid
        out += write_u32(len(payload))
        out += payload

        if len(payload) & 1:
            out += b"\x00"

    return bytes(out)


def should_remove_chunk(chunk):

    if chunk.id in REMOVE_CHUNKS:

        if chunk.id != b"LIST":
            return True

        list_type, items = parse_list_chunk(chunk)

        if list_type == b"adtl":
            return True

        filtered = []

        for cid, payload in items:

            if cid in (
                b"labl",
                b"ltxt",
                b"note",
            ):
                continue

            filtered.append((cid, payload))

        if len(filtered) != len(items):
            chunk.data = build_list_chunk(
                list_type,
                filtered
            )
            chunk.size = len(chunk.data)

        return False

    return False


def collect_chunks(buf):

    result = []

    for chunk in iter_chunks(buf):

        if should_remove_chunk(chunk):
            continue

        result.append(chunk)

    return result

def build_riff(chunks, riff_type=RIFF):

    out = bytearray()

    out += riff_type
    out += b"\x00\x00\x00\x00"
    out += WAVE

    for chunk in chunks:

        out += chunk.id
        out += write_u32(len(chunk.data))
        out += chunk.data

        if len(chunk.data) & 1:
            out += b"\x00"

    riff_size = len(out) - 8

    if riff_type == RIFF:
        out[4:8] = write_u32(riff_size)
    else:
        out[4:8] = b"\xff\xff\xff\xff"

    return bytes(out)


def replace_file(path, data):

    directory = os.path.dirname(path)

    fd, tmp = tempfile.mkstemp(
        suffix=".wav",
        dir=directory
    )

    os.close(fd)

    try:

        with open(tmp, "wb") as f:
            f.write(data)

        shutil.move(tmp, path)

    finally:

        if os.path.exists(tmp):
            os.remove(tmp)


def clean_wav(path):

    with open(path, "rb") as f:
        buf = f.read()

    if not is_riff(buf):
        return False

    riff_type = buf[:4]

    original_chunks = list(iter_chunks(buf))
    new_chunks = collect_chunks(buf)

    if len(original_chunks) == len(new_chunks):

        identical = True

        for a, b in zip(original_chunks, new_chunks):

            if (
                a.id != b.id or
                a.size != b.size or
                a.data != b.data
            ):
                identical = False
                break

        if identical:
            return False

    new_data = build_riff(
        new_chunks,
        riff_type
    )

    replace_file(path, new_data)

    return True

def scan_file(path):

    with open(path, "rb") as f:
        buf = f.read()

    if not is_riff(buf):
        return {
            "valid": False,
            "chunks": [],
            "loop_chunks": []
        }

    chunks = []
    loop_chunks = []

    for chunk in iter_chunks(buf):

        name = chunk.id.decode("ascii", errors="replace")

        chunks.append(name)

        if chunk.id in REMOVE_CHUNKS:
            loop_chunks.append(name)

        elif chunk.id == b"LIST":

            list_type, items = parse_list_chunk(chunk)

            if list_type == b"adtl":
                loop_chunks.append("LIST/adtl")

            else:

                for cid, _ in items:

                    if cid in (
                        b"labl",
                        b"ltxt",
                        b"note",
                    ):
                        loop_chunks.append(
                            "LIST/" +
                            cid.decode("ascii")
                        )

    return {
        "valid": True,
        "chunks": chunks,
        "loop_chunks": loop_chunks
    }


def clean_directory(folder):

    processed = 0
    modified = 0
    failed = 0

    for root, _, files in os.walk(folder):

        for file in files:

            if not file.lower().endswith(".wav"):
                continue

            processed += 1

            path = os.path.join(root, file)

            try:

                if clean_wav(path):
                    modified += 1

            except Exception:
                failed += 1

    return {
        "processed": processed,
        "modified": modified,
        "failed": failed
    }


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:

        print("Usage:")
        print("python wav_cleaner.py <folder>")
        raise SystemExit(1)

    result = clean_directory(sys.argv[1])

    print()
    print("Processed :", result["processed"])
    print("Modified  :", result["modified"])
    print("Failed    :", result["failed"])
# EOF
