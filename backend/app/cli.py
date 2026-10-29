"""CLI: python -m app.cli INPUT OUTPUT [--lang eng]. Output format comes from OUTPUT extension."""
import argparse
import os
import sys

from .errors import ConversionError
from .services import capabilities


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="openconvert")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--lang", default="eng")
    a = p.parse_args(argv)

    kind = capabilities.kind_for_extension(os.path.splitext(a.input)[1])
    target = os.path.splitext(a.output)[1].lstrip(".").lower()
    adapter = capabilities.get_adapter(kind, target) if kind else None
    if adapter is None:
        print(f"Unsupported conversion. Supported outputs for this input: "
              f"{capabilities.outputs_for(kind) if kind else 'none'}", file=sys.stderr)
        return 2

    def progress(cur, total):
        print(f"page {cur}/{total}", file=sys.stderr)

    try:
        adapter(a.input, a.output, a.lang, progress)
    except ConversionError as exc:
        print(f"Error [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
