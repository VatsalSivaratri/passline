"""
Export Depth Anything V2 metric (ViT-S, Hypersim) to ONNX, then INT8.

  python tools/export_depth_onnx.py --checkpoint backend/checkpoints/depth_anything_v2_metric_hypersim_vits.pth \
      --da2-root backend/Depth-Anything-V2

Writes models/dav2_fp32.onnx and models/dav2_int8.onnx.
"""

import argparse
import sys
from pathlib import Path

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from onnxruntime.quantization.shape_inference import quant_pre_process

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from services.depth_backends import INPUT_SIZE, build_torch_model

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True)
ap.add_argument("--da2-root", required=True)
ap.add_argument("--out-dir", default="models")
a = ap.parse_args()

out = Path(a.out_dir)
out.mkdir(exist_ok=True)
fp32, prep, int8 = out / "dav2_fp32.onnx", out / "dav2_prep.onnx", out / "dav2_int8.onnx"

model = build_torch_model(a.checkpoint, a.da2_root)
x = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE)

torch.onnx.export(model, x, str(fp32), input_names=["image"], output_names=["depth"],
                  opset_version=17, dynamo=False)

quant_pre_process(str(fp32), str(prep))

quantize_dynamic(str(prep), str(int8), weight_type=QuantType.QInt8,
                 op_types_to_quantize=["MatMul"])
prep.unlink()

for p in (fp32, int8):
    print(f"{p}: {p.stat().st_size / 1e6:.1f} MB")
