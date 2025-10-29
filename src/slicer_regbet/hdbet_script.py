
from __future__ import annotations

import textwrap


def make_hdbet_script(in_vol: str, out_skull: str, out_seg: str, log_txt: str | None = None,
                      wait_timeout_s: int = 1200) -> str:
    """
    Return a Python script (to be executed inside 3D Slicer) that:
    - loads the registered volume,
    - runs HDBrainExtractionTool (HD-BET),
    - waits synchronously until a segmentation appears (or times out),
    - saves outputs (skull-stripped volume + segmentation),
    - exits(0) on success, exits(1) on failure.
    """
    code = f"""
import sys, os, importlib, slicer, logging, time
from slicer.util import saveNode
logging.getLogger().setLevel(logging.INFO)
in_vol   = r{in_vol!r}
out_vol  = r{out_skull!r}
out_seg  = r{out_seg!r}
log_path = r{(log_txt or "")!r}
timeout_s = int({wait_timeout_s})

def log(msg):
    print(msg)
    try:
        if log_path:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(msg+'\\n')
    except Exception:
        pass

def seg_count(segNode):
    try:
        return segNode.GetSegmentation().GetNumberOfSegments()
    except Exception:
        return 0

try:
    log("[HDBET] loading volume: " + in_vol)
    n = slicer.util.loadVolume(in_vol)
    if not n:
        raise RuntimeError("Failed to load input volume")

    log("[HDBET] importing HDBrainExtractionTool")
    HDBET_mod = importlib.import_module('HDBrainExtractionTool')
    logic_cls = getattr(HDBET_mod, 'HDBrainExtractionToolLogic', None)
    if logic_cls is None:
        raise RuntimeError("HDBrainExtractionToolLogic not found (install SlicerHD-BET extension)")

    skull = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode','_tmp_BET')
    seg   = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode','_tmp_SEG')

    log("[HDBET] running...")
    logic = logic_cls()
    if hasattr(logic, 'process'):
        logic.process(n, skull, seg)
    else:
        logic.run(n, skull, seg)

    # Wait until at least one segment exists or timeout
    t0 = time.time()
    last_print = -1
    while seg_count(seg) < 1 and (time.time() - t0) < timeout_s:
        slicer.app.processEvents()
        time.sleep(1.0)
        elapsed = int(time.time() - t0)
        if elapsed // 30 != last_print // 30:
            log(f"[HDBET] waiting... {{elapsed}}s")
            last_print = elapsed

    if seg_count(seg) < 1:
        raise RuntimeError("HD-BET did not produce any segment before timeout")

    seg.SetReferenceImageGeometryParameterFromVolumeNode(n)

    log("[HDBET] saving skull-stripped: " + out_vol)
    ok1 = saveNode(skull, out_vol)
    log("[HDBET] saving segmentation:  " + out_seg)
    ok2 = saveNode(seg, out_seg)

    if not ok1 or not ok2:
        raise RuntimeError("Failed to save outputs")

    log("[HDBET] DONE")
    slicer.util.exit(0)
except Exception as e:
    log("[HDBET][ERROR] " + str(e))
    try:
        slicer.util.exit(1)
    except Exception:
        import sys as _sys; _sys.exit(1)
"""
    return textwrap.dedent(code)
