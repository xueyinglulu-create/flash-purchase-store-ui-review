from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import median

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ANNOTATION_MANIFEST = []


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size, index=1 if bold and "PingFang" in candidate else 0)
        except OSError:
            continue
    return ImageFont.load_default()


def normalize(src: str, dst: str):
    im = Image.open(ASSETS / src).convert("RGB")
    im = im.resize((393, 852), Image.Resampling.LANCZOS)
    im.save(ASSETS / dst, quality=95)


def label(draw: ImageDraw.ImageDraw, xy, text: str, fill=(244, 63, 94), anchor="la"):
    f = font(18, True)
    box = draw.textbbox(xy, text, font=f, anchor=anchor, stroke_width=0)
    pad = 6
    draw.rounded_rectangle((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), radius=7, fill=(18, 24, 38, 235))
    draw.text(xy, text, font=f, fill=fill, anchor=anchor)


def arrow(draw: ImageDraw.ImageDraw, start, end, color=(244, 63, 94), width=4):
    draw.line((start, end), fill=color, width=width)
    ang = math.atan2(start[1] - end[1], start[0] - end[0])
    for delta in (-0.6, 0.6):
        p = (end[0] + 12 * math.cos(ang + delta), end[1] + 12 * math.sin(ang + delta))
        draw.line((end, p), fill=color, width=width)


def double_arrow(draw: ImageDraw.ImageDraw, start, end, color=(244, 63, 94), width=4):
    arrow(draw, start, end, color, width)
    arrow(draw, end, start, color, width)


def dimension_line(draw, start, end, orientation, text="", color=(244, 63, 94, 255)):
    """Draw an edge-anchored dimension line with perpendicular end caps."""
    width, cap = 4, 12
    draw.line((start, end), fill=color, width=width)
    if orientation == "vertical":
        for x, y in (start, end):
            draw.line((x - cap, y, x + cap, y), fill=color, width=width)
        text_xy = (start[0] - 18, round((start[1] + end[1]) / 2))
        anchor = "rm"
    else:
        for x, y in (start, end):
            draw.line((x, y - cap, x, y + cap), fill=color, width=width)
        text_xy = (round((start[0] + end[0]) / 2), start[1] - 18)
        anchor = "mb"
    if text:
        f = font(15, True)
        box = draw.textbbox(text_xy, text, font=f, anchor=anchor)
        draw.rounded_rectangle((box[0] - 4, box[1] - 3, box[2] + 4, box[3] + 3), radius=5, fill=(17, 24, 39, 230))
        draw.text(text_xy, text, font=f, fill=(251, 191, 36, 255), anchor=anchor)


def annotated_crop(src: str, crop_box, note: str, rects=(), arrows=(), dimensions=(), guides=(), target_width=620, evidence_id=""):
    """Create one tight, issue-specific crop with mapped marks and a visible Chinese note."""
    source = Image.open(ASSETS / src).convert("RGB")
    im = source.crop(crop_box)
    scale = target_width / im.width
    rendered = im.resize((target_width, round(im.height * scale)), Image.Resampling.LANCZOS)
    note_h = 74
    canvas = Image.new("RGB", (target_width, rendered.height + note_h), (17, 24, 39))
    canvas.paste(rendered, (0, 0))
    d = ImageDraw.Draw(canvas, "RGBA")

    def p(x, y):
        return (round((x - crop_box[0]) * scale), round((y - crop_box[1]) * scale))

    for x1, y1, x2, y2 in rects:
        a, b = p(x1, y1), p(x2, y2)
        d.rounded_rectangle((a[0], a[1], b[0], b[1]), radius=8, outline=(244, 63, 94, 255), width=5)
    for x1, y1, x2, y2, direction in arrows:
        a, b = p(x1, y1), p(x2, y2)
        if direction == "double":
            double_arrow(d, a, b)
        else:
            arrow(d, a, b)
    for x1, y1, x2, y2, orientation, text in dimensions:
        dimension_line(d, p(x1, y1), p(x2, y2), orientation, text)
    for x1, y1, x2, y2, text in guides:
        a, b = p(x1, y1), p(x2, y2)
        d.line((a, b), fill=(14, 165, 233, 235), width=3)
        if text:
            f = font(14, True)
            d.text((a[0] + 4, a[1] + 3), text, font=f, fill=(14, 165, 233, 255))
    d.text((18, rendered.height + 18), note, font=font(20, True), fill=(251, 191, 36))
    ANNOTATION_MANIFEST.append({
        "evidence_id": evidence_id,
        "source": src,
        "source_size": source.size,
        "logical_viewport": source.size,
        "crop_box": crop_box,
        "render_scale": scale,
        "rects_source": rects,
        "arrows_source": arrows,
        "dimensions_source": dimensions,
        "guides_source": guides,
        "endpoint_tolerance": "≤1 source px/logical unit",
    })
    return canvas


def save_issue(name: str, title: str, panels):
    framed(title, panels, width=1380 if len(panels) > 1 else 760).save(ASSETS / name)


def framed(title: str, images: list[tuple[str, Image.Image]], width=1420, bg=(244, 247, 251)):
    margin, gap, title_h = 36, 28, 72
    max_h = max(im.height for _, im in images)
    col_w = (width - margin * 2 - gap * (len(images) - 1)) // len(images)
    scaled = []
    for name, im in images:
        scale = min(col_w / im.width, 760 / im.height)
        scaled.append((name, im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)))
    canvas_h = title_h + max(im.height for _, im in scaled) + 100
    canvas = Image.new("RGB", (width, canvas_h), bg)
    d = ImageDraw.Draw(canvas)
    d.text((margin, 22), title, font=font(28, True), fill=(15, 23, 42))
    x = margin
    for name, im in scaled:
        y = title_h + 42
        canvas.paste(im, (x, y))
        d.rounded_rectangle((x - 2, y - 2, x + im.width + 2, y + im.height + 2), radius=10, outline=(203, 213, 225), width=2)
        d.text((x, title_h + 8), name, font=font(20, True), fill=(51, 65, 85))
        x += col_w + gap
    return canvas


def rgb_to_lab(rgb):
    vals = []
    for v in rgb:
        v /= 255
        vals.append(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92)
    r, g, b = vals
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722)
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    def f(v):
        return v ** (1 / 3) if v > 0.008856 else 7.787 * v + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def de76(a, b):
    la, lb = rgb_to_lab(a), rgb_to_lab(b)
    return round(sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5, 2)


def swatch_compare():
    rows = [
        ("H5 面板底色", (34, 34, 34), (35, 35, 35)),
        ("H5 价格", (255, 118, 77), (238, 127, 89)),
        ("H5 分割线", (61, 61, 61), (57, 57, 57)),
        ("Nano 消息卡底色", (32, 32, 32), (33, 33, 33)),
        ("Nano 店卡底色", (45, 45, 45), (46, 46, 46)),
        ("Nano CTA 底色", (50, 60, 95), (53, 61, 94)),
    ]
    canvas = Image.new("RGB", (1220, 550), (17, 24, 39))
    d = ImageDraw.Draw(canvas)
    d.text((36, 26), "深色模式 token：Figma 与实现采样", font=font(30, True), fill="white")
    d.text((530, 76), "Figma", font=font(20, True), fill=(203, 213, 225))
    d.text((760, 76), "实现", font=font(20, True), fill=(203, 213, 225))
    d.text((970, 76), "差异", font=font(20, True), fill=(203, 213, 225))
    data = []
    for i, (name, expected, actual) in enumerate(rows):
        y = 118 + i * 68
        d.text((36, y + 12), name, font=font(21), fill=(241, 245, 249))
        d.rounded_rectangle((520, y, 710, y + 46), radius=8, fill=expected)
        d.rounded_rectangle((750, y, 940, y + 46), radius=8, fill=actual)
        eh = "#%02X%02X%02X" % expected
        ah = "#%02X%02X%02X" % actual
        d.text((530, y + 12), eh, font=font(18, True), fill="white" if sum(expected) < 360 else "black")
        d.text((760, y + 12), ah, font=font(18, True), fill="white" if sum(actual) < 360 else "black")
        delta = tuple(actual[j] - expected[j] for j in range(3))
        d.text((970, y + 12), f"ΔRGB {delta} · ΔE76 {de76(expected, actual)}", font=font(17), fill=(251, 146, 60))
        data.append({"element": name, "expected": eh, "actual": ah, "delta_rgb": delta, "delta_e76": de76(expected, actual)})
    canvas.save(ASSETS / "evidence-dark-token-swatches.png")
    return data


def main():
    actuals = {
        "impl-nano-light-first.png": "actual-nano-light-first.png",
        "impl-nano-light-entry.png": "actual-nano-light-entry.png",
        "impl-nano-dark-first.png": "actual-nano-dark-first.png",
        "impl-nano-dark-entry.png": "actual-nano-dark-entry.png",
        "impl-h5-light-top.png": "actual-h5-light-top.png",
        "impl-h5-dark-top.png": "actual-h5-dark-top.png",
        "impl-h5-loading.png": "actual-h5-loading.png",
        "impl-h5-bottom.png": "actual-h5-bottom.png",
    }
    for src, dst in actuals.items():
        normalize(src, dst)

    # Chevron evidence: 4x crops with exact visible-ink boxes.
    f = Image.open(ASSETS / "figma-overlay-dark.png").convert("RGB").crop((320, 210, 370, 255)).resize((400, 360), Image.Resampling.NEAREST)
    a = Image.open(ASSETS / "actual-h5-dark-top.png").convert("RGB").crop((330, 95, 380, 140)).resize((400, 360), Image.Resampling.NEAREST)
    fd, ad = ImageDraw.Draw(f), ImageDraw.Draw(a)
    fd.rectangle(((334 - 320) * 8, (229 - 210) * 8, (352 - 320) * 8, (238 - 210) * 8), outline=(244, 63, 94), width=6)
    ad.rectangle(((354 - 330) * 8, (114 - 95) * 8, (365 - 330) * 8, (120 - 95) * 8), outline=(244, 63, 94), width=6)
    label(fd, (18, 325), "可见墨迹 18×9pt；frame 24×24pt")
    label(ad, (18, 325), "可见墨迹约 11×6pt；frame 截图不可见")
    framed("下拉图标尺寸（同一几何口径）", [("Figma", f), ("H5 实现", a)], width=960).save(ASSETS / "evidence-icon-chevron.png")

    # Loading/empty-state overview.
    initial = Image.open(ASSETS / "figma-state-initial-loading.png").convert("RGB")
    refresh = Image.open(ASSETS / "figma-state-refresh-loading.png").convert("RGB")
    loading = Image.open(ASSETS / "actual-h5-loading.png").convert("RGB")
    trip = framed("状态独立核对：初始空态 / 刷新加载 / 实现加载", [("Figma 初始空态", initial), ("Figma 刷新中", refresh), ("实现加载中", loading)], width=1500)
    td = ImageDraw.Draw(trip, "RGBA")
    label(td, (55, trip.height - 52), "初始空态：41×41 图标 + 23pt 图文间距；实现证据缺失", (251, 191, 36))
    label(td, (1010, trip.height - 52), "实现 spinner 约 23×22pt；设计 41×40pt", (244, 63, 94))
    trip.save(ASSETS / "evidence-state-loading.png")

    # Per-issue embedded evidence. Every issue card receives one concrete annotated image.
    save_issue("issue-ui-01.png", "UI-01 · 价格异常值进入界面", [
        ("H5 加载态", annotated_crop("actual-h5-loading.png", (0, 150, 393, 790), "多行现价显示 ¥NaN；旧价仍正常", rects=((18, 270, 374, 307), (18, 508, 374, 535), (18, 742, 374, 770)))),
    ])
    nano_spacing = framed("UI-02 · Nano 商品文字堆叠（可见墨迹边缘口径）", [
        ("Figma", annotated_crop(
            "figma-card-light.png", (100, 340, 305, 575),
            "销量→价格：2pt ×3；第3个价格→推荐语：14pt",
            dimensions=(
                (292, 386, 292, 388, "vertical", "2"),
                (292, 450, 292, 452, "vertical", "2"),
                (292, 514, 292, 516, "vertical", "2"),
                (292, 526, 292, 540, "vertical", "14"),
            ),
            target_width=520, evidence_id="UI-02-figma",
        )),
        ("Nano 实现", annotated_crop(
            "actual-nano-light-entry.png", (130, 295, 320, 545),
            "销量→价格：12pt ×3；第3个价格→推荐语：24pt",
            dimensions=(
                (308, 333, 308, 345, "vertical", "12"),
                (308, 397, 308, 409, "vertical", "12"),
                (308, 461, 308, 473, "vertical", "12"),
                (308, 483, 308, 507, "vertical", "24"),
            ),
            target_width=520, evidence_id="UI-02-actual",
        )),
    ], width=1380)
    nano_spacing.save(ASSETS / "evidence-nano-vertical-spacing.png")
    nano_spacing.save(ASSETS / "issue-ui-02.png")
    save_issue("issue-ui-03.png", "UI-03 · 店卡到更多入口的水平空隙", [
        ("Figma", annotated_crop(
            "figma-card-light.png", (270, 265, 365, 645), "卡片右边→入口左边：10pt",
            dimensions=((290, 455, 300, 455, "horizontal", "10pt"),),
            target_width=360, evidence_id="UI-03-figma",
        )),
        ("Nano 实现", annotated_crop(
            "actual-nano-light-entry.png", (285, 225, 380, 610), "卡片右边→入口左边：6pt，少4pt",
            dimensions=((312, 455, 318, 455, "horizontal", "6pt"),),
            target_width=360, evidence_id="UI-03-actual",
        )),
    ])
    save_issue("issue-ui-04.png", "UI-04 · 浮层起点与高度", [
        ("Figma", annotated_crop("figma-overlay-light.png", (0, 130, 375, 812), "浮层顶 y=203；高度 609pt", rects=((0, 203, 374, 811),))),
        ("H5 实现", annotated_crop("actual-h5-light-top.png", (0, 40, 393, 852), "浮层顶 y≈86；高度≈766pt", rects=((0, 86, 392, 851),))),
    ])
    save_issue("issue-ui-05.png", "UI-05 · 浮层标题文案不一致", [
        ("Figma", annotated_crop("figma-overlay-light.png", (0, 190, 375, 275), "设计：逛逛发现更多", rects=((18, 215, 190, 249),))),
        ("H5 实现", annotated_crop("actual-h5-light-top.png", (0, 78, 393, 160), "实现：更多店铺", rects=((18, 102, 113, 135),))),
    ])
    Image.open(ASSETS / "evidence-icon-chevron.png").save(ASSETS / "issue-ui-06.png")
    save_issue("issue-ui-07.png", "UI-07 · 刷新 spinner 尺寸与上方留白", [
        ("Figma", annotated_crop(
            "figma-state-refresh-loading.png", (130, 680, 235, 805), "墨迹约39×40pt；内容底→图标顶约30pt",
            rects=((168, 746, 207, 786),),
            dimensions=((218, 716, 218, 746, "vertical", "30pt"),),
            target_width=500, evidence_id="UI-07-figma",
        )),
        ("H5 实现", annotated_crop(
            "actual-h5-loading.png", (150, 745, 235, 852), "墨迹约21×21pt；分割线→图标顶约36pt",
            rects=((186, 807, 207, 828),),
            dimensions=((220, 771, 220, 807, "vertical", "36pt"),),
            target_width=500, evidence_id="UI-07-actual",
        )),
    ])
    save_issue("issue-ui-08.png", "UI-08 · 到底文案到底边留白", [
        ("Figma", annotated_crop(
            "figma-state-bottom.png", (115, 715, 270, 812), "文字底→面板底：51pt",
            dimensions=((255, 761, 255, 812, "vertical", "51pt"),),
            target_width=560, evidence_id="UI-08-figma",
        )),
        ("H5 实现", annotated_crop(
            "actual-h5-bottom.png", (115, 785, 285, 852), "文字底→面板底：23pt，少28pt",
            dimensions=((270, 829, 270, 852, "vertical", "23pt"),),
            target_width=560, evidence_id="UI-08-actual",
        )),
    ])
    Image.open(ASSETS / "issue-ui-08.png").save(ASSETS / "evidence-state-end-spacing.png")
    save_issue("issue-ui-09.png", "UI-09 · H5 深色面板底色 token", [
        ("Figma", annotated_crop("figma-overlay-dark.png", (0, 190, 375, 340), "面板底色 #222222", rects=((8, 208, 367, 332),))),
        ("H5 实现", annotated_crop("actual-h5-dark-top.png", (0, 78, 393, 235), "稳定采样 #232323（+1/+1/+1）", rects=((8, 87, 385, 228),))),
    ])
    save_issue("issue-ui-10.png", "UI-10 · H5 深色价格色 token", [
        ("Figma", annotated_crop("figma-overlay-dark.png", (0, 305, 375, 485), "价格应为 #FF764D", rects=((18, 421, 360, 465),))),
        ("H5 实现", annotated_crop("actual-h5-dark-top.png", (0, 190, 393, 380), "实采约 #EE7F59，ΔE76≈12.6", rects=((18, 305, 378, 352),))),
    ])
    save_issue("issue-ui-11.png", "UI-11 · H5 深色分割线 token", [
        ("Figma", annotated_crop("figma-overlay-dark.png", (0, 420, 375, 520), "分割线 #3D3D3D", rects=((18, 466, 357, 470),))),
        ("H5 实现", annotated_crop("actual-h5-dark-top.png", (0, 320, 393, 430), "实现 #393939，偏暗", rects=((18, 363, 375, 368),))),
    ])
    save_issue("issue-ui-12.png", "UI-12 · Nano 深色消息卡与店卡表面", [
        ("Figma", annotated_crop("figma-card-dark.png", (0, 105, 375, 690), "消息卡 #202020；店卡 #2D2D2D", rects=((12, 116, 363, 674), (60, 238, 314, 589)))),
        ("Nano 实现", annotated_crop("actual-nano-dark-entry.png", (0, 105, 393, 690), "实现分别 #212121 / #2E2E2E", rects=((12, 126, 381, 677), (61, 207, 314, 575)))),
    ])
    save_issue("issue-ui-13.png", "UI-13 · Nano 深色 CTA 合成色", [
        ("Figma", annotated_crop("figma-card-dark.png", (45, 510, 330, 650), "CTA 合成约 #323C5F", rects=((60, 565, 315, 610),))),
        ("Nano 实现", annotated_crop("actual-nano-dark-entry.png", (45, 485, 335, 625), "实现约 #353D5E", rects=((60, 525, 314, 580),))),
    ])
    save_issue("issue-ui-14.png", "UI-14 · H5 商品图片外框尺寸", [
        ("Figma", annotated_crop("figma-overlay-light.png", (0, 285, 150, 455), "图片外框 82×82pt", rects=((18, 326, 100, 408),))),
        ("H5 实现", annotated_crop("actual-h5-light-top.png", (0, 165, 165, 350), "图片外框约 86×86pt（+4×+4）", rects=((20, 213, 106, 299),))),
    ])
    save_issue("issue-ui-15.png", "UI-15 · 商品图片渲染为纯黑块", [
        ("H5 加载态", annotated_crop("actual-h5-loading.png", (250, 145, 393, 335), "第 4 个商品图为纯黑失败占位", rects=((316, 177, 373, 262),))),
    ])
    save_issue("issue-ui-16.png", "UI-16 · 商品列累计向右漂移", [
        ("Figma", annotated_crop(
            "figma-overlay-light.png", (10, 305, 375, 455),
            "列左边：20 / 114 / 208 / 302；列步距94pt",
            guides=(
                (20, 320, 20, 448, "20"),
                (114, 320, 114, 448, "114"),
                (208, 320, 208, 448, "208"),
                (302, 320, 302, 448, "302"),
            ),
            target_width=700, evidence_id="UI-16-figma",
        )),
        ("H5 实现", annotated_crop(
            "actual-h5-light-top.png", (10, 190, 393, 345),
            "列左边：20 / 119 / 218 / 317；累计漂移0/+5/+10/+15pt",
            guides=(
                (20, 205, 20, 340, "20"),
                (119, 205, 119, 340, "119"),
                (218, 205, 218, 340, "218"),
                (317, 205, 317, 340, "317"),
            ),
            target_width=700, evidence_id="UI-16-actual",
        )),
    ])
    save_issue("issue-ui-17.png", "UI-17 · 右侧第 4 列被过度截断", [
        ("Figma", annotated_crop(
            "figma-overlay-light.png", (275, 305, 375, 455),
            "82pt 图片中可见约73pt；隐藏约9pt",
            dimensions=((302, 316, 375, 316, "horizontal", "可见73"),),
            target_width=500, evidence_id="UI-17-figma",
        )),
        ("H5 实现", annotated_crop(
            "actual-h5-light-top.png", (285, 190, 393, 345),
            "86pt 图片中仅可见约54pt；隐藏约32pt",
            dimensions=((317, 205, 371, 205, "horizontal", "可见54"),),
            guides=((371, 195, 371, 342, "裁切线371"),),
            target_width=500, evidence_id="UI-17-actual",
        )),
    ])

    # Overall comparisons.
    nano = framed("Nano 店铺卡片与更多入口", [
        ("Figma", annotated_crop(
            "figma-card-light.png", (0, 0, 375, 963), "设计：文本堆叠 + 入口 gap 10pt",
            rects=((40, 274, 290, 634), (300, 274, 350, 634)),
            target_width=500, evidence_id="overview-nano-figma",
        )),
        ("实现 · iPhone 15", annotated_crop(
            "actual-nano-light-entry.png", (0, 0, 393, 852), "实现：文本竖向空隙增大 + 入口 gap 6pt",
            rects=((61, 240, 312, 600), (318, 240, 367, 600)),
            target_width=500, evidence_id="overview-nano-actual",
        )),
    ], width=1080)
    nano.save(ASSETS / "overview-nano.png")
    h5 = framed("H5 更多店铺浮层", [
        ("Figma", annotated_crop(
            "figma-overlay-light.png", (0, 0, 375, 812), "设计：列步距94pt；末列隐藏约9pt",
            rects=((0, 203, 374, 811),),
            guides=((20, 320, 20, 448, ""), (114, 320, 114, 448, ""), (208, 320, 208, 448, ""), (302, 320, 302, 448, "")),
            target_width=500, evidence_id="overview-h5-figma",
        )),
        ("实现 · iPhone 15", annotated_crop(
            "actual-h5-light-top.png", (0, 0, 393, 852), "实现：列步距99pt；末列隐藏约32pt",
            rects=((0, 86, 392, 851),),
            guides=((20, 205, 20, 340, ""), (119, 205, 119, 340, ""), (218, 205, 218, 340, ""), (317, 205, 317, 340, "")),
            target_width=500, evidence_id="overview-h5-actual",
        )),
    ], width=1080)
    h5.save(ASSETS / "overview-h5.png")

    colors = swatch_compare()
    measurements = {
        "device": {"model": "iPhone 15", "logical_viewport": "393×852pt", "screenshot": "1179×2556px", "scale": "3px/pt"},
        "empty_initial_design": {"container_h": 549, "top_blank": 239, "icon_visible": "41×41", "icon_copy_gap": 23, "copy_visible": "40×13", "bottom_blank": 233, "residual": 0, "stack_center_delta": 3},
        "refresh_loading": {"design_spinner": "39×40", "actual_spinner": "21×21", "delta": "-18×-19", "design_content_to_spinner": 30, "actual_content_to_spinner": 36},
        "end_state": {"design_text": "47×11", "actual_text": "53×14", "design_bottom_gap": 51, "actual_bottom_gap": 23, "bottom_gap_delta": -28},
        "h5_columns": {"design_left_edges": [20, 114, 208, 302], "actual_left_edges": [20, 119, 218, 317], "design_pitch": 94, "actual_pitch": 99, "cumulative_drift": [0, 5, 10, 15]},
        "h5_right_clip": {"design_tile": 82, "design_visible": 73, "design_hidden": 9, "actual_tile": 86, "actual_visible": 54, "actual_hidden": 32},
        "icons": {"sheet_chevron_design_frame": "24×24", "sheet_chevron_design_ink": "18×9", "sheet_chevron_actual_frame": "Needs verification", "sheet_chevron_actual_ink": "11×6"},
        "dark_colors": colors,
    }
    (ROOT / "measurements.json").write_text(json.dumps(measurements, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "annotation-manifest.json").write_text(json.dumps(ANNOTATION_MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
