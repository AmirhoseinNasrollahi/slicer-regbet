from __future__ import annotations

import argparse
from pathlib import Path

from .core import run_batch


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="slicer-regbet",
        description="Batch: Affine to atlas (BRAINSFit 12-DOF) + HD-BET (headless) with categorized outputs"
    )
    p.add_argument("--in-dir", required=True, help="Input directory containing images.")
    p.add_argument("--atlas", required=True, help="Fixed atlas volume path (e.g., MNI template).")
    p.add_argument("--out-dir", required=True, help="Output directory.")
    p.add_argument("--pattern", default=None, help="Glob pattern, e.g., '*T1*.nii.gz'.")
    p.add_argument("--recursive", action="store_true", help="Search input directory recursively.")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    p.add_argument("--iterations", type=int, default=1500, help="BRAINSFit max iterations (1500).")
    p.add_argument("--sampling", type=float, default=0.05, help="BRAINSFit sampling percentage (0.05).")
    p.add_argument("--bet-timeout", type=int, default=1800, help="Max seconds to wait for HD-BET (1800).")
    p.add_argument("--log-level", default="INFO", help="Logging level: DEBUG, INFO, WARNING, ERROR.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    return run_batch(
        in_dir=Path(args.in_dir),
        atlas=Path(args.atlas),
        out_dir=Path(args.out_dir),
        pattern=args.pattern,
        recursive=args.recursive,
        overwrite=args.overwrite,
        iterations=args.iterations,
        sampling=args.sampling,
        bet_timeout=args.bet_timeout,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    raise SystemExit(main())