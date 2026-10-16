#!/usr/bin/env python3
"""把一条轨迹（KML / GPX）按地形标出 CP 点，并导出带 <wpt> 的 GPX。

为什么默认出 GPX 而不是 KML：华为运动健康的「导入路线」只吃轨迹线，
KML 里的 <Placemark><Point> 一律不显示；GPX 的 <wpt> 才会被识别成路径点。

CP 选点规则（按地形，不做等分）：
  1. 起点、终点必设（闭合环线合并成「起点 / 终点」）
  2. 取显著的峰（相对周边 ±600 m 最低点的高差 ≥ --prominence）与全局谷底
  3. 相邻 CP 间距超过 --max-gap 时，在中间按等距补点
  4. 丢弃与前一个 CP 距离小于 --min-gap 的候选

里程口径：三维（水平距离 + 高程差）累计，与两步路一致。
爬升口径：±50 m 滑动平均后的剖面累加，避免 GPS 高程噪声虚高。
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

R = 6371008.8
KML_NS = {"k": "http://www.opengis.net/kml/2.2", "gx": "http://www.google.com/kml/ext/2.2"}


# ---------------------------------------------------------------- 基础几何
def haversine(a, b):
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp, dl = p2 - p1, math.radians(b[0] - a[0])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def cumulative(points):
    """三维累计里程（米）"""
    seg = [0.0]
    for i in range(1, len(points)):
        d = math.hypot(haversine(points[i - 1][:2], points[i][:2]),
                       points[i][2] - points[i - 1][2])
        seg.append(seg[-1] + d)
    return seg


def smooth(points, seg, win):
    """按沿轨迹距离做滑动平均（±win 米）"""
    out = []
    for i in range(len(points)):
        j, k = i, i
        while j > 0 and seg[i] - seg[j] < win:
            j -= 1
        while k < len(points) - 1 and seg[k] - seg[i] < win:
            k += 1
        out.append(sum(p[2] for p in points[j:k + 1]) / (k - j + 1))
    return out


def gain_between(sm, lo, hi):
    g = l = 0.0
    for i in range(lo + 1, hi + 1):
        d = sm[i] - sm[i - 1]
        if d > 0:
            g += d
        else:
            l -= d
    return g, l


# ---------------------------------------------------------------- 读取轨迹
def _coords_from_text(text):
    out = []
    for chunk in text.split():
        parts = [float(x) for x in chunk.split(",")]
        if len(parts) >= 2:
            out.append((parts[0], parts[1], parts[2] if len(parts) > 2 else 0.0))
    return out


def load_track(path):
    """返回 (points, source_kind)；points = [(lon, lat, ele), ...]"""
    if path.lower().endswith(".gpx"):
        root = ET.parse(path).getroot()
        ns = {"g": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        pts = []
        for tp in root.findall(".//g:trkpt", ns) or root.findall(".//trkpt"):
            ele = tp.findtext("g:ele", default=None, namespaces=ns) or tp.findtext("ele")
            pts.append((float(tp.get("lon")), float(tp.get("lat")),
                        float(ele) if ele else 0.0))
        if not pts:
            for w in root.findall(".//g:wpt", ns) or root.findall(".//wpt"):
                pts.append((float(w.get("lon")), float(w.get("lat")), 0.0))
        return pts, "gpx"

    root = ET.parse(path).getroot()
    coords = root.findall(".//gx:Track/gx:coord", KML_NS)
    if coords:
        return [tuple(float(x) for x in c.text.split()) for c in coords], "kml:gx:Track"
    for ls in root.findall(".//k:LineString", KML_NS):
        pts = _coords_from_text(ls.findtext("k:coordinates", default="", namespaces=KML_NS))
        if len(pts) > 1:
            return pts, "kml:LineString"
    pts = []
    for pm in root.findall(".//k:Placemark", KML_NS):
        c = pm.findtext("k:Point/k:coordinates", default="", namespaces=KML_NS)
        if c.strip():
            pts.extend(_coords_from_text(c))
    return pts, "kml:Point"


# ---------------------------------------------------------------- 选 CP
def pick_cps(seg, sm, smw, opts):
    """候选 = 显著峰 + 全局谷底；再按 max_cps 裁剪、按 max_gap 补点"""
    n = len(seg)
    total = seg[-1]

    # 判定峰谷的邻域半径：路线短时自动收窄，否则窗口会覆盖整条轨迹
    win = min(opts.window, max(100.0, total / 10))

    def win_idx(i, w):
        j, k = i, i
        while j > 0 and seg[i] - seg[j] < w:
            j -= 1
        while k < n - 1 and seg[k] - seg[i] < w:
            k += 1
        return j, k

    # --- 峰：邻域内的最大值，且与邻域最低点的高差够大
    cands = []
    i = 0
    while i < n:
        j, k = win_idx(i, win)
        mx = max(range(j, k + 1), key=lambda x: smw[x])
        if j < mx < k:
            prom = smw[mx] - min(smw[j:k + 1])
            if prom >= opts.prominence:
                cands.append({"i": mx, "kind": "peak", "score": prom})
        i = max(k + 1, i + 1)

    # --- 低点：排除两端 15% 后取最低点。起终点本身常就是全线最低点，
    #     所以这里要的是「中途最低点」——最后一段长爬升的起点
    mid = [i for i in range(n) if 0.15 * total <= seg[i] <= 0.85 * total]
    if mid:
        mn = min(mid, key=lambda x: smw[x])
        relief = max(smw) - smw[mn]
        if relief >= opts.prominence:
            cands.append({"i": mn, "kind": "valley", "score": relief})

    # --- 去重：间距不足时保留得分高的
    cands.sort(key=lambda c: c["i"])
    merged = []
    for c in cands:
        if merged and seg[c["i"]] - seg[merged[-1]["i"]] < opts.min_gap:
            if c["score"] > merged[-1]["score"]:
                merged[-1] = c
            continue
        merged.append(c)

    # --- 端点最高优先
    keep = [{"i": 0, "kind": "start", "score": float("inf")},
            {"i": n - 1, "kind": "end", "score": float("inf")}]
    for c in merged:
        if seg[c["i"]] < opts.min_gap or total - seg[c["i"]] < opts.min_gap:
            continue
        if all(abs(seg[c["i"]] - seg[x["i"]]) >= opts.min_gap for x in keep):
            keep.append(c)
    keep.sort(key=lambda c: c["i"])

    # --- 裁剪到 max_cps：优先删得分最低、且删掉后不超 max_gap 的
    while len(keep) > opts.max_cps:
        removed = False
        for c in sorted([x for x in keep[1:-1]], key=lambda x: x["score"]):
            idx = keep.index(c)
            if seg[keep[idx + 1]["i"]] - seg[keep[idx - 1]["i"]] <= opts.max_gap:
                keep.remove(c)
                removed = True
                break
        if not removed:
            break

    # --- 补点：间距超上限时按等距插入（基准取插入前的上一个 CP，不能被新插入的点带跑）
    filled = [keep[0]]
    for c in keep[1:]:
        base = filled[-1]["i"]
        gap = seg[c["i"]] - seg[base]
        if gap > opts.max_gap:
            pieces = math.ceil(gap / opts.max_gap)
            for m in range(1, pieces):
                target = seg[base] + gap * m / pieces
                idx = min(range(n), key=lambda x: abs(seg[x] - target))
                if all(abs(seg[idx] - seg[x["i"]]) >= opts.min_gap for x in filled):
                    filled.append({"i": idx, "kind": "filler", "score": 0.0})
        filled.append(c)
    return filled


def name_cps(cps, points, seg, sm, smw, opts):
    total = seg[-1]
    loop = haversine(points[cps[0]["i"]][:2], points[cps[-1]["i"]][:2]) < 300
    # 峰按行进顺序编号（第 1 峰 = 第一个山头），与「最高点」区分开
    peak_rank = {}
    r = 0
    for c in cps:
        if c["kind"] == "peak":
            r += 1
            peak_rank[id(c)] = r
    peaks = [c for c in cps if c["kind"] == "peak"]
    top = max(peaks, key=lambda c: sm[c["i"]], default=None)
    gmin = min(range(len(points)), key=lambda x: smw[x])

    for k, c in enumerate(cps):
        if k == 0:
            c["name"] = "起点 / 终点" if loop else "起点"
        elif k == len(cps) - 1:
            c["name"] = "终点（与起点同址）" if loop else "终点"
        elif c["kind"] == "valley":
            c["name"] = ("全线最低点（谷底）" if smw[c["i"]] <= smw[gmin] + 1
                         else "中途最低点（谷底）")
        elif c is top:
            c["name"] = "全线最高点（第 %d 峰）" % peak_rank[id(c)]
        elif c["kind"] == "peak":
            c["name"] = "第 %d 峰" % peak_rank[id(c)]
        else:
            c["name"] = "里程点"
        c["along"] = seg[c["i"]]
        c["ele"] = points[c["i"]][2]
    for k, c in enumerate(cps):
        lo = cps[k - 1]["i"] if k else 0
        c["seg_dist"] = c["along"] - (cps[k - 1]["along"] if k else 0)
        c["seg_gain"] = gain_between(sm, lo, c["i"])[0] if k else 0.0
        c["cum_gain"] = gain_between(sm, 0, c["i"])[0]
    return cps


# ---------------------------------------------------------------- 输出
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_gpx(path, points, cps, name, desc):
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<gpx version="1.1" creator="route-cp" '
         'xmlns="http://www.topografix.com/GPX/1/1" '
         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
         'http://www.topografix.com/GPX/1/1/gpx.xsd">',
         '  <metadata>',
         f'    <name>{esc(name)}（含 {len(cps)} 个 CP）</name>',
         f'    <desc>{esc(desc)}</desc>',
         '  </metadata>']
    for k, c in enumerate(cps, 1):
        lon, lat, ele = points[c["i"]]
        d = ("里程 %.2f km / 海拔 %.0f m / 累计爬升 %.0f m" %
             (c["along"] / 1000, c["ele"], c["cum_gain"]))
        if k > 1:
            d += " / 本段 %.0f m（爬升 %.0f m）" % (c["seg_dist"], c["seg_gain"])
        L += [f'  <wpt lat="{lat:.8f}" lon="{lon:.8f}">',
              f'    <ele>{ele:.2f}</ele>',
              f'    <name>CP{k} {esc(c["name"])}</name>',
              f'    <desc>{esc(d)}</desc>',
              '    <sym>Flag, Blue</sym>',
              '    <type>CP</type>',
              '  </wpt>']
    L += ['  <trk>', f'    <name>{esc(name)}</name>', '    <trkseg>']
    for lon, lat, ele in points:
        L.append(f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}"><ele>{ele:.2f}</ele></trkpt>')
    L += ['    </trkseg>', '  </trk>', '</gpx>', '']
    open(path, "w", encoding="utf-8").write("\n".join(L))


def write_kml(path, points, cps, name, desc):
    """KML 版本：元素顺序必须 name → description → styleUrl → ExtendedData → Point"""
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2" '
         'xmlns:gx="http://www.google.com/kml/ext/2.2">',
         '  <Document>',
         f'    <name>{esc(name)}</name>',
         '    <visibility>1</visibility>']
    for k in range(1, len(cps) + 1):
        L += [f'    <Style id="cpStyle{k}">',
              '      <IconStyle>',
              '        <scale>1.15</scale>',
              '        <Icon>',
              f'          <href>http://maps.google.com/mapfiles/kml/paddle/{min(k, 10)}.png</href>',
              '        </Icon>',
              '      </IconStyle>',
              '    </Style>']
    L += ['    <Folder>', f'      <name>CP点（{len(cps)} 个）</name>', '      <visibility>1</visibility>']
    for k, c in enumerate(cps, 1):
        lon, lat, ele = points[c["i"]]
        d = ("里程 %.2f km / 海拔 %.0f m / 累计爬升 %.0f m" %
             (c["along"] / 1000, c["ele"], c["cum_gain"]))
        L += [f'      <Placemark id="cpPoint{k}">',
              f'        <name>{esc("CP%d · %s" % (k, c["name"]))}</name>',
              f'        <description><![CDATA[<div>{esc(d)}</div>]]></description>',
              f'        <styleUrl>#cpStyle{k}</styleUrl>',
              '        <ExtendedData>',
              '          <Data name="CPIndex">',
              f'            <value>{k}</value>',
              '          </Data>',
              '          <Data name="DistanceAlongTrack">',
              f'            <value>{c["along"]:.1f}</value>',
              '          </Data>',
              '        </ExtendedData>',
              '        <Point>',
              f'          <coordinates>{lon:.7f},{lat:.7f},{ele:.2f}</coordinates>',
              '        </Point>',
              '      </Placemark>']
    L += ['    </Folder>', '    <Folder>', '      <name>轨迹</name>', '      <visibility>1</visibility>',
          '      <Placemark>', '        <name>轨迹</name>',
          '        <LineString>', '          <coordinates>']
    L.append("".join(f"{lon:.7f},{lat:.7f},{ele:.2f} " for lon, lat, ele in points))
    L += ['          </coordinates>', '        </LineString>', '      </Placemark>', '    </Folder>',
          '  </Document>', '</kml>', '']
    open(path, "w", encoding="utf-8").write("\n".join(L))


def validate(path, schema_dir=None):
    try:
        subprocess.run(["xmllint", "--noout", path], check=True,
                       capture_output=True)
    except FileNotFoundError:
        return "跳过（未装 xmllint）"
    except subprocess.CalledProcessError as e:
        return "XML 错误：" + e.stderr.decode()[:300]
    if schema_dir:
        xsd = os.path.join(schema_dir, "gpx11.xsd")
        if os.path.exists(xsd):
            r = subprocess.run(["xmllint", "--noout", "--schema", xsd, path],
                               capture_output=True)
            return "gpx.xsd 校验" + ("通过" if r.returncode == 0 else "失败：" + r.stderr.decode()[:300])
    return "良构"


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser(description="给轨迹标 CP 点并导出 GPX")
    ap.add_argument("input", help="轨迹文件（.kml 或 .gpx）")
    ap.add_argument("-o", "--outdir", default=None, help="输出目录（默认与输入同目录）")
    ap.add_argument("-n", "--name", default=None, help="路线名（默认取输入文件名）")
    ap.add_argument("--format", choices=["gpx", "kml", "both"], default="gpx")
    ap.add_argument("--max-gap", type=float, default=2000, help="CP 最大间距（米），默认 2000")
    ap.add_argument("--min-gap", type=float, default=250, help="CP 最小间距（米），默认 250")
    ap.add_argument("--max-cps", type=int, default=10, help="CP 数量上限，默认 10")
    ap.add_argument("--prominence", type=float, default=50, help="峰/谷显著性阈值（米），默认 50")
    ap.add_argument("--window", type=float, default=600, help="判定峰谷的邻域半径（米），默认 600")
    ap.add_argument("--quiet", action="store_true")
    opts = ap.parse_args()

    points, kind = load_track(opts.input)
    if len(points) < 2:
        sys.exit("读不到轨迹点：%s" % opts.input)
    seg = cumulative(points)
    sm = smooth(points, seg, 50)     # 爬升统计
    smw = smooth(points, seg, 100)   # 峰谷判定
    total = seg[-1]
    name = opts.name or re.sub(r"\.[^.]+$", "", os.path.basename(opts.input))

    cps = pick_cps(seg, sm, smw, opts)
    cps = name_cps(cps, points, seg, sm, smw, opts)

    outdir = opts.outdir or os.path.dirname(os.path.abspath(opts.input))
    os.makedirs(outdir, exist_ok=True)
    stem = re.sub(r"\.[^.]+$", "", os.path.basename(opts.input))
    desc = ("轨迹全长 %.2f km / 累计爬升 %.0f m；CP 按地形取点（峰 %d、谷 %d、补点 %d）" %
            (total / 1000, gain_between(sm, 0, len(points) - 1)[0],
             sum(1 for c in cps if c["kind"] == "peak"),
             sum(1 for c in cps if c["kind"] == "valley"),
             sum(1 for c in cps if c["kind"] == "filler")))
    written = []
    if opts.format in ("gpx", "both"):
        p = os.path.join(outdir, stem + "_CP.gpx")
        write_gpx(p, points, cps, name, desc)
        written.append(p)
    if opts.format in ("kml", "both"):
        p = os.path.join(outdir, stem + "_CP.kml")
        write_kml(p, points, cps, name, desc)
        written.append(p)

    if not opts.quiet:
        print("输入：%s（%s，%d 点）" % (opts.input, kind, len(points)))
        print("轨迹：%.2f km，累计爬升 %.0f m" % (total / 1000, gain_between(sm, 0, len(points) - 1)[0]))
        print()
        print("| CP | 名称 | 里程 (km) | 本段 (m) | 海拔 (m) | 累计爬升 (m) | 本段爬升 (m) |")
        print("|---:|---|---:|---:|---:|---:|---:|")
        for k, c in enumerate(cps, 1):
            print("| %d | %s | %.2f | %s | %.0f | %.0f | %s |" % (
                k, c["name"], c["along"] / 1000,
                "—" if k == 1 else "%.0f" % c["seg_dist"], c["ele"], c["cum_gain"],
                "—" if k == 1 else "%.0f" % c["seg_gain"]))
        gaps = [cps[i]["seg_dist"] for i in range(1, len(cps))]
        if gaps:
            print("\n站间：最小 %.0f m / 最大 %.0f m" % (min(gaps), max(gaps)))
        print()
        for p in written:
            print("已写入 %s（%s）" % (p, validate(p)))


if __name__ == "__main__":
    main()
