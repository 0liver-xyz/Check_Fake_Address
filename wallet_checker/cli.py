from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from pathlib import Path

from wallet_checker.balance import fetch_balance
from wallet_checker.validate import Coin, validate_address


def _data_txt_files(data_dir: Path) -> list[Path]:
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {data_dir}")
    files = sorted(data_dir.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt files in {data_dir}")
    return files


def _iter_address_lines(data_dir: Path) -> Iterator[tuple[Path, int, str]]:
    for path in _data_txt_files(data_dir):
        with path.open(encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, start=1):
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                yield path, line_no, s


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _run_single(
    address: str,
    coin_arg: Coin | None,
    no_balance: bool,
) -> int:
    ok, coin, msg = validate_address(address, coin=coin_arg)

    print(f"Valid: {ok}")
    print(f"Detail: {msg}")
    if coin:
        print(f"Coin: {coin}")

    if not ok:
        return 1

    if no_balance:
        return 0

    assert coin is not None
    try:
        res = fetch_balance(address.strip(), coin)
    except Exception as e:
        print(f"Balance error: {e}", file=sys.stderr)
        return 2

    print(f"Balance: {res.balance} {res.unit}")
    return 0


def _run_batch(
    data_dir: Path,
    coin_arg: Coin | None,
    no_balance: bool,
) -> int:
    data_dir = data_dir.resolve()
    worst = 0
    n_invalid = 0
    n_balance_err = 0

    for path, line_no, addr in _iter_address_lines(data_dir):
        label = f"{_rel(path, data_dir)}:{line_no}"
        ok, coin, msg = validate_address(addr, coin=coin_arg)
        parts = [label, addr, f"valid={ok}", f"detail={msg}"]
        if coin:
            parts.append(f"coin={coin}")
        else:
            parts.append("coin=-")

        if not ok:
            n_invalid += 1
            worst = max(worst, 1)
            print("\t".join(parts))
            continue

        assert coin is not None
        if no_balance:
            print("\t".join(parts))
            continue

        try:
            res = fetch_balance(addr.strip(), coin)
            parts.append(f"balance={res.balance} {res.unit}")
            print("\t".join(parts))
        except Exception as e:
            n_balance_err += 1
            worst = max(worst, 2)
            parts.append(f"balance_error={e}")
            print("\t".join(parts), file=sys.stderr)

    if n_invalid or n_balance_err:
        print(
            f"Summary: invalid={n_invalid} balance_errors={n_balance_err}",
            file=sys.stderr,
        )
    return worst


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Check whether an address is structurally valid and fetch its on-chain balance.",
    )
    p.add_argument(
        "address",
        nargs="?",
        default=None,
        help="Single address to check. If omitted, read every non-empty line from all .txt files under --data-dir.",
    )
    p.add_argument(
        "--data-dir",
        default="data",
        help="Directory of .txt input files (one address per line) when address is omitted (default: data).",
    )
    p.add_argument(
        "--coin",
        choices=("btc", "eth"),
        default=None,
        help="Force coin type instead of auto-detect",
    )
    p.add_argument(
        "--no-balance",
        action="store_true",
        help="Only validate the address, do not call public APIs",
    )
    args = p.parse_args(argv)

    coin_arg: Coin | None = args.coin

    if args.address is not None:
        return _run_single(args.address, coin_arg, args.no_balance)

    try:
        return _run_batch(Path(args.data_dir), coin_arg, args.no_balance)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
