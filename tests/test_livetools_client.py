from livetools.client import format_snapshot


def test_format_snapshot_basic():
    snap = {"addr": "12345678", "bpId": "1", "hitCount": "5"}
    out = format_snapshot(snap)
    assert "=== BREAKPOINT HIT === 0x12345678 (bp#1, hit #5)" in out

    # Test missing prefix and default "????????", "?", "?"
    snap_empty = {}
    out_empty = format_snapshot(snap_empty)
    assert "=== BREAKPOINT HIT === 0x???????? (bp#?, hit #?)" in out_empty


def test_format_snapshot_x86_regs():
    snap = {
        "addr": "0x123",
        "regs": {
            "_arch": "x86",
            "eax": "00000001",
            "ebx": "00000002",
            "eip": "12345678",
            "esp": "AABBCCDD",
        },
    }
    out = format_snapshot(snap)
    assert "  EAX=00000001  EBX=00000002  ECX=       ?  EDX=       ?" in out
    assert "  ESI=       ?  EDI=       ?  EBP=       ?  ESP=AABBCCDD" in out
    assert "  EIP=12345678" in out


def test_format_snapshot_x64_regs():
    snap = {
        "addr": "0x123",
        "regs": {
            "_arch": "x64",
            "rax": "0000000000000001",
            "r15": "AABBCCDDEEFF1122",
            "rip": "1111222233334444",
        },
    }
    out = format_snapshot(snap)
    assert (
        "  RAX=0000000000000001  RBX=               ?  RCX=               ?  RDX=               ?"
        in out
    )
    assert (
        "  R12=               ?  R13=               ?  R14=               ?  R15=AABBCCDDEEFF1122"
        in out
    )
    assert "  RIP=1111222233334444" in out


def test_format_snapshot_stack():
    snap_x86 = {
        "addr": "0x123",
        "regs": {"_arch": "x86", "esp": "1000"},
        "stack": ["val1", "val2", "val3", "val4", "val5"],
    }
    out_x86 = format_snapshot(snap_x86)
    assert "Stack [ESP=1000]:" in out_x86
    # 4 bytes per slot in x86
    assert "  +00: val1  +04: val2  +08: val3  +0C: val4" in out_x86
    assert "  +10: val5" in out_x86

    snap_x64 = {
        "addr": "0x123",
        "regs": {"_arch": "x64", "rsp": "2000"},
        "stack": ["v1", "v2", "v3", "v4", "v5"],
    }
    out_x64 = format_snapshot(snap_x64)
    assert "Stack [RSP=2000]:" in out_x64
    # 8 bytes per slot in x64
    assert "  +00: v1  +08: v2  +10: v3  +18: v4" in out_x64
    assert "  +20: v5" in out_x64


def test_format_snapshot_disasm():
    snap = {
        "addr": "0x123",
        "disasm": [
            {"addr": "0x1000", "str": "mov eax, 1"},
            {"addr": "0x1002", "str": "nop"},
            {"addr": "0x1003", "str": "ret"},
        ],
    }
    out = format_snapshot(snap)
    assert "Disasm @ EIP:" in out
    assert "> 0x1000  mov eax, 1" in out
    assert "  0x1002  nop" in out
    assert "  0x1003  ret" in out
