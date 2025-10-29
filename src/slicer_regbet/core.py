
from __future__ import annotations

import glob
import logging
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from .hdbet_script import make_hdbet_script

VALID_EXTS = (".nii", ".nii.gz", ".nrrd", ".mha", ".mhd", ".nifti", ".hdr", ".img")


def basename_no_nii_gz(p: Path) -> str:
    b = p.name
    if b.endswith(".nii.gz"):
        return b[:-7]
    return Path(b).stem


def find_images(in_dir: Path, pattern: str | None = None, recursive: bool = False) -> List[Path]:
    if pattern:
        pattern_path = str(in_dir / ("**" if recursive else "") / pattern)
        paths = glob.glob(pattern_path, recursive=recursive)
        return sorted([Path(p) for p in paths if Path(p).is_file()])
    out: List[Path] = []
    if recursive:
        for root, _, files in os.walk(in_dir):
            for f in files:
                if f.lower().endswith(VALID_EXTS):
                    out.append(Path(root) / f)
    else:
        for f in os.listdir(in_dir):
            if f.lower().endswith(VALID_EXTS):
                out.append(in_dir / f)
    return sorted(out)


def nonzero_file(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except Exception:
        return False


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def slicer_executable() -> Path:
    env = os.environ.get("SLICER_EXE")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    py_exec = Path(sys.executable)
    candidate = (py_exec.parent.parent / "Slicer.exe").resolve()
    return candidate


@dataclass
class Paths:
    reg_dir: Path
    bet_dir: Path
    seg_dir: Path
    log_dir: Path
    xfm_dir: Path


def setup_output_dirs(out_dir: Path) -> Paths:
    reg_dir = out_dir / "register"
    bet_dir = out_dir / "bet"
    seg_dir = out_dir / "segment"
    log_dir = out_dir / "log"
    xfm_dir = out_dir / "transform"
    ensure_dirs(reg_dir, bet_dir, seg_dir, log_dir, xfm_dir)
    return Paths(reg_dir, bet_dir, seg_dir, log_dir, xfm_dir)


def run_subprocess(cmd: Sequence[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    logging.debug("Running command: %s", " ".join(shlex.quote(c) for c in cmd))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def run_registration(slicer, atlas, mov, out_reg, out_xfm, iterations: int, sampling: float) -> bool:
    cmd = [
        str(slicer), "--launch", "BRAINSFit",
        "--fixedVolume", str(atlas),
        "--movingVolume", str(mov),
        "--outputVolume", str(out_reg),
        "--outputTransform", str(out_xfm),
        "--useAffine",
        "--initializeTransformMode", "useMomentsAlign",
        "--numberOfIterations", str(iterations),
        "--samplingPercentage", str(sampling),
        "--debugLevel", "10",
        "--failureExitCode", "1",
    ]
    res = run_subprocess(cmd)
    if res.stdout:
        logging.info(res.stdout.strip())
    if res.returncode != 0:
        if res.stderr:
            logging.error(res.stderr.strip())
        return False
    return True


def run_hdbet(slicer, out_reg, out_bet, out_seg, bet_log, bet_timeout: int) -> bool:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w", encoding="utf-8") as tf:
        tf.write(make_hdbet_script(str(out_reg), str(out_bet), str(out_seg), str(bet_log),
                                   wait_timeout_s=bet_timeout))
        tmp_py = Path(tf.name)

    try:
        cmd = [str(slicer), "--no-main-window", "--no-splash", "--python-script", str(tmp_py)]
        res = run_subprocess(cmd, timeout=bet_timeout + 120)
        if res.stdout:
            logging.info(res.stdout.strip())
        if res.stderr:
            logging.info(res.stderr.strip())
        return res.returncode == 0 and nonzero_file(out_bet) and nonzero_file(out_seg)
    except subprocess.TimeoutExpired:
        logging.error("HD-BET timeout (> %ss).", bet_timeout)
        return False
    finally:
        try:
            tmp_py.unlink(missing_ok=True)
        except Exception:
            pass


def process_case(idx: int, total: int, mov, atlas, out_paths, overwrite: bool,
                 iterations: int, sampling: float, slicer, bet_timeout: int) -> bool:
    name = basename_no_nii_gz(mov)
    out_reg = out_paths.reg_dir / f"{name}_register.nii.gz"
    out_xfm = out_paths.xfm_dir / f"{name}_to_MNI.h5"
    out_bet = out_paths.bet_dir / f"{name}_register_BET.nii.gz"
    out_seg = out_paths.seg_dir / f"{name}_register_SEG.seg.nrrd"
    bet_log = out_paths.log_dir / f"{name}_hdbet.log"

    if (nonzero_file(out_reg) and nonzero_file(out_xfm) and nonzero_file(out_bet) and nonzero_file(out_seg)
            and not overwrite):
        logging.info("[SKIP] (%d/%d) All outputs exist for: %s", idx, total, name)
        return True

    logging.info("[RUN ] (%d/%d) %s", idx, total, name)

    if not nonzero_file(out_reg) or overwrite:
        ok = run_registration(slicer, atlas, mov, out_reg, out_xfm, iterations, sampling)
        if not ok:
            logging.error("[FAIL] BRAINSFit failed for %s", name)
            return False
    else:
        logging.info("[INFO] Registered volume exists, skipping registration.")

    if (not nonzero_file(out_bet)) or (not nonzero_file(out_seg)) or overwrite:
        ok2 = run_hdbet(slicer, out_reg, out_bet, out_seg, bet_log, bet_timeout)
        if not ok2:
            logging.error("[FAIL] HD-BET failed or timed out for %s", name)
            return False
    else:
        logging.info("[INFO] BET outputs exist, skipping HD-BET.")

    logging.info("[OK  ] Registered : %s (%s)", out_reg, "OK" if nonzero_file(out_reg) else "MISSING/0B")
    logging.info("[OK  ] Transform  : %s (%s)", out_xfm, "OK" if nonzero_file(out_xfm) else "MISSING/0B")
    logging.info("[OK  ] BET volume : %s (%s)", out_bet, "OK" if nonzero_file(out_bet) else "MISSING/0B")
    logging.info("[OK  ] BET seg    : %s (%s)", out_seg, "OK" if nonzero_file(out_seg) else "MISSING/0B")
    logging.info("[LOG ] HD-BET log : %s (%s)", bet_log, "OK" if bet_log.exists() else "MISSING")
    return True


def run_batch(in_dir, atlas, out_dir, pattern, recursive: bool,
              overwrite: bool, iterations: int, sampling: float, bet_timeout: int,
              log_level: str = "INFO") -> int:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    out_paths = setup_output_dirs(out_dir)

    slicer = slicer_executable()
    if not slicer.is_file():
        logging.error("Slicer launcher not found. Set SLICER_EXE environment variable or install 3D Slicer.")
        return 2
    if not atlas.is_file():
        logging.error("Atlas not found: %s", atlas)
        return 2

    imgs = find_images(in_dir, pattern, recursive)
    if not imgs:
        logging.error("No input images found.")
        return 1

    logging.info("[INFO] Launcher : %s", slicer)
    logging.info("[INFO] Inputs   : %d files", len(imgs))
    logging.info("[INFO] Atlas    : %s", atlas)
    logging.info("[INFO] Out dir  : %s", out_dir)
    logging.info("-" * 50)

    done = 0
    for idx, mov in enumerate(imgs, start=1):
        ok = process_case(
            idx, len(imgs), mov, atlas, out_paths, overwrite, iterations, sampling, slicer, bet_timeout
        )
        done += int(ok)
        logging.info("-" * 50)

    logging.info("[SUMMARY] Completed %d/%d cases.", done, len(imgs))
    return 0 if done == len(imgs) else 1
