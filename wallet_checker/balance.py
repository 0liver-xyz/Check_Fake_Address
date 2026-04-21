from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import requests

Coin = Literal["btc", "eth"]

BLOCKSTREAM = "https://blockstream.info/api"
BLOCKSCOUT_ETH = "https://eth.blockscout.com/api/v2"


@dataclass
class BalanceResult:
    coin: Coin
    address: str
    balance: Decimal
    unit: str
    raw: dict


def _btc_sats_to_btc(sats: int) -> Decimal:
    return Decimal(sats) / Decimal(10**8)


def fetch_btc_balance(address: str, timeout: int = 30) -> BalanceResult:
    url = f"{BLOCKSTREAM}/address/{address}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    chain = data.get("chain_stats") or {}
    funded = int(chain.get("funded_txo_sum", 0))
    spent = int(chain.get("spent_txo_sum", 0))
    sats = funded - spent
    return BalanceResult(
        coin="btc",
        address=address,
        balance=_btc_sats_to_btc(sats),
        unit="BTC",
        raw=data,
    )


def fetch_eth_balance(address: str, timeout: int = 30) -> BalanceResult:
    url = f"{BLOCKSCOUT_ETH}/addresses/{address}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    wei = int(data.get("coin_balance", "0"))
    bal = Decimal(wei) / Decimal(10**18)
    return BalanceResult(
        coin="eth",
        address=address,
        balance=bal,
        unit="ETH",
        raw=data,
    )


def fetch_balance(address: str, coin: Coin, timeout: int = 30) -> BalanceResult:
    if coin == "btc":
        return fetch_btc_balance(address, timeout=timeout)
    return fetch_eth_balance(address, timeout=timeout)
