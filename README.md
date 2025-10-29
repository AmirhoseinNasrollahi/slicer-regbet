# slicer-regbet

Batch registration to an atlas using **BRAINSFit (affine, 12-DOF)** and skull-stripping with **HD-BET** inside **3D Slicer**, all from a clean **CLI** interface.  
Outputs are organized into subfolders: `register/`, `transform/`, `bet/`, `segment/`, and `log/`.

> ⚠️ **Requirements**
> - 3D Slicer 5.x (ensure both `Slicer` / `Slicer.exe` and `PythonSlicer` are available)
> - **SlicerHD-BET** extension (module: `HDBrainExtractionTool`)
> - Windows, Linux, or macOS.  
>   On non-Windows systems, define the `SLICER_EXE` environment variable.

---

## Features
- Fully **headless batch processing** via `slicer-regbet` CLI  
- **BRAINSFit** registration (affine 12-DOF, moments alignment, configurable iterations & sampling)  
- **HD-BET** skull-stripping inside Slicer (synchronous execution with timeout and logs)  
- **Idempotent pipeline** — automatically skips cases with complete existing outputs (`--overwrite` to recompute)  
- Predictable **directory structure** and file naming  
- Verbose **logging** with timestamps and levels  
- Cross-platform **launcher detection** (`SLICER_EXE` override supported)

---

## Installation

### Editable install
```bash
pip install -U pip
pip install -e .
```

### Virtual environment (recommended)
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e .
```

---

## CLI Quickstart
```bash
slicer-regbet   --in-dir /path/to/input   --atlas /path/to/MNI.nii.gz   --out-dir /path/to/output   --pattern "*.nii.gz"   --recursive   --iterations 1500   --sampling 0.05   --bet-timeout 1800   --log-level INFO
```

### Arguments
| Argument | Description |
|-----------|--------------|
| `--in-dir` | Input directory containing MRI volumes (`.nii`, `.nii.gz`, `.nrrd`, `.mha`, `.mhd`, etc.) |
| `--atlas` | Fixed atlas (e.g., MNI template) |
| `--out-dir` | Output directory (automatically creates subfolders) |
| `--pattern` | Optional glob pattern (e.g., `*T1*.nii.gz`) |
| `--recursive` | Recursively search inside input directory |
| `--overwrite` | Recompute even if outputs exist |
| `--iterations` | Maximum BRAINSFit iterations (default `1500`) |
| `--sampling` | BRAINSFit sampling percentage (default `0.05`) |
| `--bet-timeout` | Maximum seconds to wait for HD-BET (default `1800`) |
| `--log-level` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

---

## Processing Pipeline

### 1️⃣ Registration (BRAINSFit)
- Method: affine, 12 degrees of freedom  
- Initialization: moments alignment  
- Outputs:
  - `register/{name}_register.nii.gz`
  - `transform/{name}_to_MNI.h5`

### 2️⃣ Brain Extraction (HD-BET)
- Runs synchronously inside Slicer via the `HDBrainExtractionTool` logic
- Outputs:
  - `bet/{name}_register_BET.nii.gz`
  - `segment/{name}_register_SEG.seg.nrrd`
  - `log/{name}_hdbet.log`

> ✅ If all outputs are present and non-empty, the case will be skipped unless `--overwrite` is provided.

---

## Output Directory Layout
```
output/
├─ register/    # registered volumes
├─ transform/   # transforms (.h5)
├─ bet/         # skull-stripped volumes
├─ segment/     # HD-BET segmentations (.seg.nrrd)
└─ log/         # log files per case
```

---

## 3D Slicer Notes

- **Windows**: the launcher is auto-detected next to `PythonSlicer.exe`  
- **Linux/macOS**: specify manually if needed:
  ```bash
  export SLICER_EXE=/Applications/Slicer.app/Contents/MacOS/Slicer   # macOS example
  # or for Linux:
  export SLICER_EXE=/opt/Slicer/Slicer
  ```

---

## Troubleshooting

| Issue | Possible Fix |
|-------|---------------|
| `Slicer not found` | Set `SLICER_EXE` to the path of the launcher |
| `HDBrainExtractionTool not found` | Install **SlicerHD-BET** extension |
| `HD-BET timeout` | Increase `--bet-timeout` (slow CPU/GPU) |
| Registration artifacts | Adjust `--iterations` / `--sampling` |
| No files processed | Check `--pattern`, extensions, or `--recursive` flag |

---

## Development
```bash
ruff check src
pytest -q
```

### Project Layout
```
src/slicer_regbet/
├─ cli.py          # CLI entrypoint and argument parser
├─ core.py         # batch orchestration, BRAINSFit & HD-BET logic
└─ hdbet_script.py # in-Slicer Python generator for HD-BET
```

---

## Performance Tips
- Increase `--iterations` for higher accuracy  
- Adjust `--sampling` (0.02–0.1) for speed vs. precision  
- Use SSDs for input/output for better I/O performance  
- On GPU builds of HD-BET, ensure CUDA is properly configured  

---

## License
MIT © Amirhosein Nasrollahi - Amirkabir university

---

## Citation
If you use this tool in academic or scientific work, please cite:

- **3D Slicer:** https://www.slicer.org/  
- **BRAINSFit** (part of Slicer registration framework)  
- **HD-BET:** Isensee, F. et al., *Medical Image Analysis* (2019)
