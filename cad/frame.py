"""桌面机器人 1mm 黄铜棒框架：按 source/wiring-1.png 标注尺寸参数化建模。

图纸证据（wiring-1.png，单位毫米）：
  八边形闭合轮廓，边长 10 / 29 / 28.41 / 14 / 14 / 35 / 16 / 28，
  对应内角 150 / 133 / 137 / 131 / 139 / 136 / 134 / 120（和恰为 1080°）。
  另有图纸内部绿色线段连接 P7-P4，未标注长度，按图推算，状态为需核对。
"""

import json
import math
import os
from pathlib import Path

from build123d import Cylinder, Location, Rotation, Sphere, Vector, export_step, export_stl

OUT_DIR = Path(__file__).resolve().parent
ROD_DIAMETER = 1.0

# 顶点 P1..P8 按图纸位置顺时针：左上→右上→右肩→右下→底右→底左→左下→左肩
INTERIOR_ANGLES = [150.0, 133.0, 137.0, 131.0, 139.0, 136.0, 134.0, 120.0]
# EDGE[i] 为 P(i+1) -> P(i+2) 的边长（EDGE[7] 为 P8 -> P1）
EDGE_LENGTHS = [29.0, 28.41, 14.0, 14.0, 35.0, 16.0, 28.0, 10.0]
EDGE_NAMES = [
    "P1-P2 顶边",
    "P2-P3 右上斜边",
    "P3-P4 右边",
    "P4-P5 右下斜边",
    "P5-P6 底边",
    "P6-P7 左下斜边",
    "P7-P8 左边",
    "P8-P1 左上斜边",
]


def unit(v):
    n = math.sqrt(v.X**2 + v.Y**2 + v.Z**2)
    return Vector(v.X / n, v.Y / n, v.Z / n)


def midpoint(a, b):
    return Vector((a.X + b.X) / 2, (a.Y + b.Y) / 2, (a.Z + b.Z) / 2)


def build_centerline():
    """按标注边长与内角顺时针走线，返回闭合残差与修正后的顶点。"""
    pts = [Vector(0.0, 0.0, 0.0)]
    heading = 0.0
    for i in range(8):
        d = Vector(math.cos(math.radians(heading)), math.sin(math.radians(heading)), 0.0)
        pts.append(pts[-1] + d * EDGE_LENGTHS[i])
        heading -= 180.0 - INTERIOR_ANGLES[(i + 1) % 8]
    gap = pts[0] - pts[8]
    residual = gap.length
    corrected = [pts[i] + gap * (i / 8.0) for i in range(8)]
    cx = (max(v.X for v in corrected) + min(v.X for v in corrected)) / 2
    cy = (max(v.Y for v in corrected) + min(v.Y for v in corrected)) / 2
    corrected = [Vector(v.X - cx, v.Y - cy, 0.0) for v in corrected]
    return residual, corrected


def measure(vertices):
    n = len(vertices)
    edges = [round((vertices[(i + 1) % n] - vertices[i]).length, 4) for i in range(n)]
    angles = []
    for i in range(n):
        a = unit(vertices[(i - 1) % n] - vertices[i])
        b = unit(vertices[(i + 1) % n] - vertices[i])
        cos = max(-1.0, min(1.0, a.dot(b)))
        angles.append(round(math.degrees(math.acos(cos)), 4))
    return edges, angles


def build_frame(vertices):
    rod_r = ROD_DIAMETER / 2.0
    segments = [(i, (i + 1) % 8) for i in range(8)]
    segments.append((6, 3))  # P7 -> P4 内部斜撑，图纸绿色绘制但未标注

    solids = []
    for a, b in segments:
        p1, p2 = vertices[a], vertices[b]
        d = p2 - p1
        theta = math.degrees(math.atan2(d.Y, d.X))
        loc = Location(midpoint(p1, p2)) * Rotation(0, 0, theta) * Rotation(0, 90, 0)
        solids.append(loc * Cylinder(rod_r, d.length))
    solids += [Location(v) * Sphere(rod_r) for v in vertices]
    return solids


def main():
    # OCCT 在本机对含中文的绝对路径导出 STL 会失败，切到目录后用相对文件名
    os.chdir(OUT_DIR)
    residual, verts = build_centerline()
    edges_mm, angles_deg = measure(verts)
    brace_len = (verts[3] - verts[6]).length
    max_edge_dev = max(abs(edges_mm[i] - EDGE_LENGTHS[i]) for i in range(8))

    solids = build_frame(verts)
    frame = solids[0]
    for extra in solids[1:]:
        frame += extra

    step_path = Path("brass-frame.step")
    stl_path = Path("brass-frame.stl")
    json_path = Path("brass-frame.json")
    export_step(frame, str(step_path))
    if not export_stl(frame, str(stl_path), tolerance=0.02):
        raise RuntimeError(f"STL 导出失败: {stl_path}")

    payload = {
        "source": "source/wiring-1.png 桌面机器人框架图纸尺寸（单位：毫米）",
        "rodDiameterMm": ROD_DIAMETER,
        "unit": "mm",
        "plane": "XY",
        "vertices": [{"id": f"P{i + 1}", "x": round(v.X, 4), "y": round(v.Y, 4)} for i, v in enumerate(verts)],
        "nominalEdges": [
            {"name": EDGE_NAMES[i], "nominalMm": EDGE_LENGTHS[i], "modelMm": edges_mm[i]} for i in range(8)
        ],
        "nominalAngles": [
            {"vertex": f"P{i + 1}", "nominalDeg": INTERIOR_ANGLES[i], "modelDeg": angles_deg[i]} for i in range(8)
        ],
        "brace": {
            "from": "P7",
            "to": "P4",
            "modelMm": round(brace_len, 3),
            "status": "需核对",
            "note": "图纸中与轮廓同色（绿色）绘制，但未标注长度；长度由标注尺寸推算，需人工核对是否真为杆件。",
        },
        "closure": {
            "rawResidualMm": round(residual, 4),
            "maxEdgeDeviationMm": round(max_edge_dev, 4),
            "note": "走线闭合残差按顶点线性分摊，来源于图纸角度取整。",
        },
        "boundingBox": {
            "widthMm": round(max(v.X for v in verts) - min(v.X for v in verts), 3),
            "heightMm": round(max(v.Y for v in verts) - min(v.Y for v in verts), 3),
            "drawingDimensionMm": 44.15,
            "drawingDimensionNote": "图纸 44.15 为顶边到底边的垂直距离，用作比例交叉校验",
        },
        "quantity": {"status": "未确认", "note": "图纸只画一片框架，是否左右各一片未在笔记中说明。"},
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"闭合残差(修正前) = {residual:.4f} mm   边长最大偏差 = {max_edge_dev:.4f} mm")
    print("边长 标注 -> 模型:")
    for i in range(8):
        print(f"  {EDGE_NAMES[i]:<14} {EDGE_LENGTHS[i]:>7.2f} -> {edges_mm[i]:>7.2f}")
    print("内角 标注 -> 模型:")
    print("  " + "  ".join(f"{INTERIOR_ANGLES[i]:.0f}->{angles_deg[i]:.1f}" for i in range(8)))
    print(f"斜撑 P7-P4 = {brace_len:.2f} mm (需核对)")
    bb = frame.bounding_box()
    print(f"包围盒 = {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
    print(f"体积 = {frame.volume:.2f} mm3   表面积 = {frame.area:.2f} mm2   实体数 = {len(frame.solids())}")
    for p in (step_path, stl_path, json_path):
        print(f"  {p.name}  {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
