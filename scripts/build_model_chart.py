"""Draw the README chart comparing the three item-name classifiers, on a dark surface.

    uv run --no-project --with matplotlib python -m scripts.build_model_chart

The numbers are the three models' shared comparison in docs/results/classification.md: the same seven real item
names, accuracy, CPU seconds for 1,000 names, model bytes and peak process memory. Seven names is a small test, so
the chart says so. Writes docs/assets/model-comparison.png (Microsoft JhengHei, so it runs on Windows).
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import PathPatch
from matplotlib.path import Path as BezierPath
from matplotlib.transforms import IdentityTransform

ROOT = Path(__file__).resolve().parents[1]
FONTS = Path("C:/Windows/Fonts")
DPI = 200

# docs/results/classification.md, "歷史同一份保留集比較": BERT is seed 42, chosen before the test was opened.
MODELS = ["TF-IDF＋邏輯迴歸", "Embedding＋邏輯迴歸", "BERT 微調"]
METRICS = [
    {"title": "答對題數", "note": "共 7 題，越多越好", "values": [6, 5, 7], "limit": 7,
     "label": lambda v: f"{v} / 7", "reference": (3, "全猜最常見的類別：3 題")},
    {"title": "分類 1,000 個品名", "note": "CPU 秒數，越少越好", "values": [0.0144, 2.6630, 16.5508],
     "label": lambda v: f"{v:.2f} 秒" if v < 1 else f"{v:.1f} 秒"},
    {"title": "模型檔大小", "note": "MB，越小越好", "values": [705209 / 1e6, 96491852 / 1e6, 409678372 / 1e6],
     "label": lambda v: f"{v:.1f} MB" if v < 10 else f"{v:,.0f} MB"},
    {"title": "執行時記憶體", "note": "峰值 MB，越少越好", "values": [125378560 / 1e6, 450252800 / 1e6, 1152663552 / 1e6],
     "label": lambda v: f"{v:,.0f} MB"},
]
TITLE = "三種品名分類模型：BERT 答對最多，但也最慢、最大"
SUBTITLE = "同一份 7 個真實品名的開發比較。樣本很少，差 1 題就差 14 個百分點，只能看出大致的取捨。"
FOOTNOTE = ("BERT 用事先選定的訓練種子；另外兩個種子各答對 7 題、6 題。速度與記憶體是 CPU 上的單次量測。\n"
            "這是較早一版模型的比較；目前選用的 BERT 另在 50 個保留的真實品名上測過，答對 42 個（84%）。"
            "資料：docs/results/classification.md、classification-real25-holdout.md")

# The dark steps of the first three categorical slots; validated all-pairs against this surface.
COLORS = {"surface": "#1a1a19", "primary": "#f0efec", "secondary": "#c3c2b7", "muted": "#898781",
          "baseline": "#383835", "series": ["#3987e5", "#d95926", "#199e70"]}


def px(points):
    return points * DPI / 72


def font(bold=False):
    return font_manager.FontProperties(fname=str(FONTS / ("msjhbd.ttc" if bold else "msjh.ttc")))


def bar(ax, row, value, color, height):
    """A bar from the baseline with a rounded data end and a square end at the baseline, drawn in pixels so the
    corner stays round whatever each panel's scale is."""
    x0, yc = ax.transData.transform((0, row))
    x1, _ = ax.transData.transform((value, row))
    x1 = max(x1, x0 + px(1.5))  # a value too small to see still leaves a sliver at the baseline
    radius = min(px(3), (x1 - x0) / 2, height / 2)
    top, bottom = yc + height / 2, yc - height / 2
    verts = [(x0, bottom), (x1 - radius, bottom), (x1, bottom), (x1, bottom + radius), (x1, top - radius),
             (x1, top), (x1 - radius, top), (x0, top), (x0, bottom)]
    codes = [BezierPath.MOVETO, BezierPath.LINETO, BezierPath.CURVE3, BezierPath.CURVE3, BezierPath.LINETO,
             BezierPath.CURVE3, BezierPath.CURVE3, BezierPath.LINETO, BezierPath.CLOSEPOLY]
    ax.add_patch(PathPatch(BezierPath(verts, codes), facecolor=color, edgecolor="none",
                           transform=IdentityTransform(), clip_on=False))
    return x1


def draw(output):
    colors = COLORS
    fig = plt.figure(figsize=(10, 4.3), dpi=DPI, facecolor=colors["surface"])
    regular, bold = font(), font(bold=True)
    fig.text(0.03, 0.93, TITLE, fontproperties=bold, fontsize=15, color=colors["primary"], va="top")
    fig.text(0.03, 0.845, SUBTITLE, fontproperties=regular, fontsize=9.5, color=colors["secondary"], va="top")
    fig.text(0.03, 0.035, FOOTNOTE, fontproperties=regular, fontsize=7.5, color=colors["muted"], va="bottom",
             linespacing=1.6)

    rows = range(len(MODELS))
    top, height = 0.66, 0.42  # the panels' area, as figure fractions
    label_width, left, gap = 0.18, 0.03, 0.025
    width = (1 - left - label_width - gap * len(METRICS) - 0.02) / len(METRICS)
    bar_height = px(11)

    # The legend: each model's swatch and name, once, beside its row.
    names = fig.add_axes([left, top - height, label_width, height])
    names.set_xlim(0, 1)
    names.set_ylim(len(MODELS) - 0.5, -0.5)
    names.axis("off")
    for row, model in zip(rows, MODELS):
        names.scatter([0.03], [row], s=px(5) ** 2 / 4, color=colors["series"][row], marker="s", clip_on=False)
        names.text(0.1, row, model, fontproperties=regular, fontsize=10, color=colors["primary"], va="center")

    for index, metric in enumerate(METRICS):
        x = left + label_width + gap + index * (width + gap)
        ax = fig.add_axes([x, top - height, width, height])
        ax.set_facecolor(colors["surface"])
        limit = metric.get("limit", max(metric["values"]))
        ax.set_xlim(0, limit * 1.55)
        ax.set_ylim(len(MODELS) - 0.5, -0.5)
        ax.axis("off")
        ax.axvline(0, color=colors["baseline"], linewidth=1)
        ax.text(0, -0.95, metric["title"], fontproperties=bold, fontsize=10, color=colors["primary"], va="bottom")
        ax.text(0, -0.62, metric["note"], fontproperties=regular, fontsize=8, color=colors["muted"], va="bottom")
        if "reference" in metric:
            value, label = metric["reference"]
            ax.plot([value, value], [-0.45, 2.45], color=colors["muted"], linewidth=0.8, zorder=0)
            ax.text(value, 2.75, label, fontproperties=regular, fontsize=7.5, color=colors["muted"], va="top",
                    ha="left")
        fig.canvas.draw()  # the panel's pixel geometry has to be final before the bars are laid out in pixels
        for row, value in zip(rows, metric["values"]):
            end = bar(ax, row, value, colors["series"][row], bar_height)
            label_x, _ = ax.transData.inverted().transform((end + px(4), 0))
            ax.text(label_x, row, metric["label"](value), fontproperties=regular, fontsize=9,
                    color=colors["primary"], va="center")

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=DPI, facecolor=colors["surface"])
    plt.close(fig)
    print("wrote", output.relative_to(ROOT))


if __name__ == "__main__":
    draw(ROOT / "docs/assets/model-comparison.png")
