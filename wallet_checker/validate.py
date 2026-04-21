from __future__ import annotations

from typing import Literal

import base58
from bech32 import bech32_decode, convertbits
from eth_utils import is_address, is_checksum_address

Coin = Literal["btc", "eth"]


def _valid_btc_base58check(addr: str) -> bool:
    try:
        payload = base58.b58decode_check(addr)
    except ValueError:
        return False
    if len(payload) != 21:
        return False
    version = payload[0]
    return version in (0x00, 0x05)


def _valid_btc_bech32(addr: str) -> bool:
    if len(addr) > 90:
        return False
    lowered = addr.lower()
    if lowered != addr and addr.upper() != addr:
        return False
    hrp, data = bech32_decode(addr)
    if hrp != "bc" or data is None or len(data) < 1:
        return False
    witver = data[0]
    prog = convertbits(data[1:], 5, 8, False)
    if prog is None:
        return False
    if witver == 0:
        return len(prog) in (20, 32)
    if witver == 1:
        return len(prog) == 32
    return False


def validate_btc(addr: str) -> bool:
    s = addr.strip()
    if not s:
        return False
    if s.lower().startswith("bc1"):
        return _valid_btc_bech32(s)
    if s.startswith("1") or s.startswith("3"):
        return _valid_btc_base58check(s)
    return False


def validate_eth(addr: str) -> bool:
    s = addr.strip()
    if not s:
        return False
    if not is_address(s):
        return False
    body = s[2:]
    has_lower = any(c.islower() for c in body)
    has_upper = any(c.isupper() for c in body)
    if has_lower and has_upper:
        return bool(is_checksum_address(s))
    return True


def detect_coin(addr: str) -> Coin | None:
    s = addr.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return "eth" if validate_eth(s) else None
    if validate_btc(s):
        return "btc"
    return None


def validate_address(addr: str, coin: Coin | None = None) -> tuple[bool, Coin | None, str]:
    """
    Return (ok, coin_if_known, message).
    """
    s = addr.strip()
    if not s:
        return False, None, "Empty address"

    if coin == "eth":
        ok = validate_eth(s)
        return ok, "eth", "Valid Ethereum address" if ok else "Invalid Ethereum address or checksum"

    if coin == "btc":
        ok = validate_btc(s)
        return ok, "btc", "Valid Bitcoin address" if ok else "Invalid Bitcoin address"

    inferred = detect_coin(s)
    if inferred == "eth":
        return True, "eth", "Valid Ethereum address"
    if inferred == "btc":
        return True, "btc", "Valid Bitcoin address"

    if s.startswith("0x") or s.startswith("0X"):
        return False, None, "Looks like Ethereum but failed validation (wrong checksum or length)"
    if s.lower().startswith("bc1") or s.startswith("1") or s.startswith("3"):
        return False, None, "Looks like Bitcoin but failed validation (checksum or witness program)"
    return False, None, "Unrecognized address format"
