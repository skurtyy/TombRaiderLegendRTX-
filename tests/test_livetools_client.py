from livetools.client import format_snapshot


def test_format_snapshot_x86():
    snap = {
        "addr": "0x12345678",
        "bpId": "1",
        "hitCount": "5",
        "regs": {
            "_arch": "x86",
            "eax": "00000001",
            "ebx": "00000002",
            "ecx": "00000003",
            "edx": "00000004",
            "esi": "00000005",
            "edi": "00000006",
            "ebp": "00000007",
            "esp": "10000000",
            "eip": "12345678",
        },
        "stack": ["AABBCCDD", "11223344"],
        "disasm": [
            {"addr": "12345678", "str": "mov eax, 1"},
            {"addr": "1234567A", "str": "nop"},
        ],
    }

    out = format_snapshot(snap)

    # Check headers
    assert "=== BREAKPOINT HIT === 0x12345678 (bp#1, hit #5)" in out

    # Check x86 registers
    assert "EAX=00000001" in out
    assert "EBX=00000002" in out
    assert "ESP=10000000" in out
    assert "EIP=12345678" in out

    # Check stack
    assert "Stack [ESP=10000000]:" in out
    assert "+00: AABBCCDD" in out
    assert "+04: 11223344" in out

    # Check disasm
    assert "Disasm @ EIP:" in out
    assert "> 12345678  mov eax, 1" in out
    assert "  1234567A  nop" in out


def test_format_snapshot_x64():
    snap = {
        "addr": "0x123456789ABCDEF0",
        "bpId": "42",
        "hitCount": "1",
        "regs": {
            "_arch": "x64",
            "rax": "1111111111111111",
            "rbx": "2222222222222222",
            "rcx": "3333333333333333",
            "rdx": "4444444444444444",
            "rsi": "5555555555555555",
            "rdi": "6666666666666666",
            "rbp": "7777777777777777",
            "rsp": "8888888888888888",
            "r8": "0000000000000008",
            "r9": "0000000000000009",
            "r10": "000000000000000A",
            "r11": "000000000000000B",
            "r12": "000000000000000C",
            "r13": "000000000000000D",
            "r14": "000000000000000E",
            "r15": "000000000000000F",
            "rip": "123456789ABCDEF0",
        },
        "stack": [
            "AAAAAAAAAAAAAAAA",
            "BBBBBBBBBBBBBBBB",
            "CCCCCCCCCCCCCCCC",
            "DDDDDDDDDDDDDDDD",
            "EEEEEEEEEEEEEEEE",  # To test wrapping row
        ],
        "disasm": [
            {"addr": "123456789ABCDEF0", "str": "mov rax, 1"},
            {"addr": "123456789ABCDEF3", "str": "nop"},
        ],
    }

    out = format_snapshot(snap, header="TEST HEADER")

    # Check headers
    assert "=== TEST HEADER === 0x123456789ABCDEF0 (bp#42, hit #1)" in out

    # Check x64 registers
    assert "RAX=1111111111111111" in out
    assert "RBX=2222222222222222" in out
    assert "R8 =0000000000000008" in out
    assert "R15=000000000000000F" in out
    assert "RIP=123456789ABCDEF0" in out

    # Check stack
    assert "Stack [RSP=8888888888888888]:" in out
    assert "+00: AAAAAAAAAAAAAAAA" in out
    assert "+08: BBBBBBBBBBBBBBBB" in out
    assert "+10: CCCCCCCCCCCCCCCC" in out
    assert "+18: DDDDDDDDDDDDDDDD" in out
    assert "+20: EEEEEEEEEEEEEEEE" in out

    # Check disasm
    assert (
        "Disasm @ EIP:" in out
    )  # Note: Function hardcodes EIP for disasm header even on x64
    assert "> 123456789ABCDEF0  mov rax, 1" in out
    assert "  123456789ABCDEF3  nop" in out


def test_format_snapshot_missing_keys():
    # Provide an almost empty dictionary to test defaults
    snap = {}

    out = format_snapshot(snap)

    # Check default header and addr padding
    assert "=== BREAKPOINT HIT === 0x????????" in out
    assert "(bp#?, hit #?)" in out

    # Should default to x86
    assert "EAX=" in out
    assert "?" * 8 in out  # default padding width for x86 missing values is 8

    # Missing stack and disasm shouldn't throw error or be printed
    assert "Stack" not in out
    assert "Disasm" not in out
