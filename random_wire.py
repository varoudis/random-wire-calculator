#!/usr/bin/env python3
"""Calculate and plot UK random-wire length estimates. Requires matplotlib."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import tempfile
import os


FT_TO_M = 0.3048
HALF_WAVE_FACTOR = 468.0  # Same empirical feet/MHz formula as the original C.


@dataclass(frozen=True)
class Band:
    name: str
    low_mhz: float
    high_mhz: float
    color: str


# UK band edges: Ofcom OFW611, Tables B/C, checked 3 October 2026.
BANDS = {
    "80": Band("80", 3.500, 3.800, "#8064A2"),
    "40": Band("40", 7.000, 7.200, "#0072B2"),
    "30": Band("30", 10.100, 10.150, "#D55E00"),
    "20": Band("20", 14.000, 14.350, "#009E73"),
    "17": Band("17", 18.068, 18.168, "#CC79A7"),
    "15": Band("15", 21.000, 21.450, "#E69F00"),
    "12": Band("12", 24.890, 24.990, "#56B4E9"),
    "10": Band("10", 28.000, 29.700, "#6F6434"),
}
CORE = ("40", "30", "20")
PROFILES = {"core": CORE, "hf": ("40", "30", "20", "17", "15", "12", "10")}
SOURCE = "https://www.ofcom.org.uk/siteassets/resources/documents/spectrum/emf/emf-amateur-licence-terms-and-conditions.pdf?v=386197"


def halfwaves(band: Band, max_ft: float) -> list[tuple[int, float, float]]:
    """All multiples whose lower edge falls within the display, including clips."""
    result = []
    n = 1
    while True:
        low = n * HALF_WAVE_FACTOR / band.high_mhz
        if low > max_ft:
            break
        high = n * HALF_WAVE_FACTOR / band.low_mhz
        result.append((n, low, min(high, max_ft)))
        n += 1
    return result


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for low, high in sorted(intervals):
        if merged and low <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(high, merged[-1][1]))
        else:
            merged.append((low, high))
    return merged


def resonance_ranges(band: Band, max_ft: float, padding_ft: float = 0) -> list[tuple[float, float]]:
    # A padded interval can reach into view even if its unpadded edge is outside.
    return [(max(0, low - padding_ft), min(max_ft, high + padding_ft))
            for _, low, high in halfwaves(band, max_ft + padding_ft)]


def blocked_ranges(bands: list[Band], max_ft: float, padding_ft: float = 0) -> list[tuple[float, float]]:
    guide = HALF_WAVE_FACTOR / min(b.low_mhz for b in bands) / 2
    intervals = [(0, min(guide, max_ft))]
    intervals.extend(
        interval for band in bands for interval in resonance_ranges(band, max_ft, padding_ft)
    )
    return merge_intervals(intervals)


def unflagged_ranges(blocked: list[tuple[float, float]], max_ft: float) -> list[tuple[float, float]]:
    result = []
    cursor = 0.0
    for low, high in blocked:
        if low > cursor:
            result.append((cursor, low))
        cursor = max(cursor, high)
    if cursor < max_ft:
        result.append((cursor, max_ft))
    return result


def make_plot(bands: list[Band], max_ft: float, padding_ft: float, unit: str, output: Path) -> None:
    # Keep plotting caches out of the project and support headless execution.
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "randomlength-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter, MultipleLocator

    primary = [band for band in bands if band.name in CORE]
    extra = [band for band in bands if band.name not in CORE]
    summaries = []
    if primary:
        summaries.append(("Main bands combined", primary))
    if extra or not primary:
        summaries.append(("All selected bands", bands))

    rows = [(label, selection, True) for label, selection in summaries]
    rows += [(f"{band.name} m", [band], False) for band in bands]
    width = 40
    height = 2.9 + 0.45 * len(rows)
    left = 2.9 / width  # Fixed room for row labels; give extra width to the scale.
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    fig.patch.set_facecolor("#FAFBFC")
    ax.set_facecolor("#FFFFFF")
    factor = FT_TO_M if unit == "m" else 1.0

    for index, (label, selection, summary) in enumerate(rows):
        ax.axhspan(index - 0.35, index + 0.35, color="#F0F3F6", zorder=0)
        guide = min(max_ft, HALF_WAVE_FACTOR / min(b.low_mhz for b in selection) / 2)
        ax.broken_barh([(0, guide * factor)], (index - 0.31, 0.62),
                       facecolors="#D8DDE3", edgecolors="#A0A8B3", hatch="///", linewidth=0.4)
        if summary:
            # Only combine resonance intervals here; the guide remains visibly distinct.
            spans = merge_intervals([
                interval for band in selection for interval in resonance_ranges(band, max_ft, padding_ft)
            ])
            ax.broken_barh([(low * factor, (high - low) * factor) for low, high in spans],
                           (index - 0.31, 0.62), facecolors="#AD4053", linewidth=0, zorder=3)
        else:
            band = selection[0]
            spans = resonance_ranges(band, max_ft, padding_ft)
            ax.broken_barh([(low * factor, (high - low) * factor) for low, high in spans],
                           (index - 0.31, 0.62), facecolors=band.color, linewidth=0, zorder=3)
            for n, low, high in halfwaves(band, max_ft):
                ax.text((low + high) / 2 * factor, index + 0.48, f"{n}×",
                        ha="center", va="center", fontsize=8, color=band.color, clip_on=True)

    labels = [row[0] for row in rows]
    ax.set_yticks(range(len(rows)), labels=labels)
    ax.set_ylim(len(rows) - 0.20, -0.55)
    ax.set_xlim(0, max_ft * factor)
    ax.tick_params(axis="y", length=0, pad=12, labelsize=11)
    for tick, (_, selection, summary) in zip(ax.get_yticklabels(), rows):
        tick.set_color("#AD4053" if summary else selection[0].color)
        if summary or selection[0].name in CORE:
            tick.set_fontweight("bold")
    # Around 135 labelled divisions fit comfortably on the wide full-size PNG.
    span = max_ft * factor
    step = next(value for value in (0.5, 1, 2.5, 5, 10, 25, 50, 100)
                if span / value <= 140)
    if unit == "ft" and max_ft <= 140:
        step = 1
    ax.xaxis.set_major_locator(MultipleLocator(step))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    ax.xaxis.set_minor_locator(MultipleLocator(step / 4))
    ax.tick_params(axis="x", which="major", labelsize=8, length=5, pad=7)
    ax.tick_params(axis="x", which="minor", length=2.5)
    ax.grid(axis="x", color="#D9DEE5", linewidth=0.7, zorder=1)
    ax.grid(axis="x", which="minor", color="#E9EDF2", linewidth=0.35, zorder=1)
    ax.set_axisbelow(True)
    ax.set_xlabel(f"Wire length ({'metres' if unit == 'm' else 'feet'})", fontsize=11, labelpad=12)
    secondary = ax.secondary_xaxis("top", functions=(
        (lambda x: x / FT_TO_M, lambda x: x * FT_TO_M) if unit == "m"
        else (lambda x: x * FT_TO_M, lambda x: x / FT_TO_M)))
    secondary_span = max_ft if unit == "m" else max_ft * FT_TO_M
    secondary_step = next(value for value in (1, 2.5, 5, 10, 25, 50, 100)
                          if secondary_span / value <= 140)
    secondary.xaxis.set_major_locator(MultipleLocator(secondary_step))
    secondary.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
    secondary.xaxis.set_minor_locator(MultipleLocator(secondary_step / 4))
    secondary.tick_params(axis="x", which="major", labelsize=9)
    secondary.set_xlabel(f"Wire length ({'feet' if unit == 'm' else 'metres'})", labelpad=9)
    for spine in ax.spines.values():
        spine.set_color("#CDD3DC")
    legend = [Patch(facecolor="#AD4053", label="Combined half-wave intervals"),
              Patch(facecolor="#D8DDE3", edgecolor="#A0A8B3", hatch="///", label="Below quarter-wave guide")]
    fig.legend(handles=legend, loc="lower left", bbox_to_anchor=(left, 0.45 / height),
               frameon=False, ncol=2, fontsize=10, borderaxespad=0)
    fig.suptitle("Random-wire length estimates · UK bands", x=left, y=1 - 0.20 / height,
                 ha="left", fontsize=19, fontweight="bold", color="#1D2939")
    band_names = ", ".join(f"{b.name} m" for b in bands)
    fig.text(left, 1 - 0.70 / height, f"Selected: {band_names}  |  Every half-wave multiple within the displayed length",
             fontsize=10, color="#526071")
    fig.text(left, 0.16 / height,
             f"468/f estimate; n× labels show half-wave multiples. Padding: {padding_ft:.2f} ft. "
             "Unshaded lengths are model gaps, not guaranteed matches.", fontsize=9, color="#526071")
    fig.subplots_adjust(left=left, right=1 - 0.4 / width, top=1 - 1.5 / height, bottom=1.35 / height)
    fig.savefig(output, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_report(bands: list[Band], max_ft: float, padding_ft: float, stem: Path) -> None:
    guide = HALF_WAVE_FACTOR / min(b.low_mhz for b in bands) / 2
    gaps = unflagged_ranges(blocked_ranges(bands, max_ft, padding_ft), max_ft)
    records = [
        {"band_m": band.name, "multiple": n, "low_ft": low, "high_ft": high,
         "low_m": low * FT_TO_M, "high_m": high * FT_TO_M,
         "clipped_at_plot_limit": n * HALF_WAVE_FACTOR / band.low_mhz > max_ft}
        for band in bands for n, low, high in halfwaves(band, max_ft)
    ]
    data = {
        "formula": "half-wave feet = 468 / MHz", "max_ft": max_ft,
        "padding_ft": padding_ft, "quarter_wave_guide_ft": guide,
        "bands": [{"band_m": b.name, "low_mhz": b.low_mhz, "high_mhz": b.high_mhz} for b in bands],
        "halfwaves": records,
        "unflagged_ranges_ft": gaps,
    }
    stem.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Random-wire length estimates", "",
             "![Coloured wire-length chart](" + stem.with_suffix(".png").name + ")", "",
             f"Display: **0–{max_ft:g} ft** (0–{max_ft * FT_TO_M:.2f} m). "
             f"Padding around half-wave intervals: **{padding_ft:g} ft**.", "",
             "## Bands", "", "| Band | UK range (MHz) | Priority |", "|---|---|---|"]
    lines += [f"| {b.name} m | {b.low_mhz:.3f}–{b.high_mhz:.3f} | "
              f"{'Main' if b.name in CORE else 'Occasional' if b.name == '80' else 'Additional'} |" for b in bands]
    lines += ["", f"Frequency limits: [Ofcom OFW611, Tables B/C]({SOURCE}), checked 3 October 2026.", "",
              "## Reading the chart", "",
              "Each band has its own colour and row. The combined rows merge its half-wave intervals; "
              "the main-band row only combines selected 40, 30 and 20 m bands. Grey hatching shows "
              "the original model's quarter-wave minimum-length guide, derived separately from "
              "the lowest frequency in each row. This is a guide, not a hard tuning limit.", "",
              f"For all selected bands, that guide is **{guide:.3f} ft** ({guide * FT_TO_M:.3f} m).", "",
              "The calculation uses the original `468 / frequency_MHz` estimate and includes every "
              "integer multiple intersecting the display, without the old six-multiple cap. "
              "Intervals crossing the right edge are clipped. Labels such as `3×` mean three half-waves.", "",
              "For an end-fed random wire, these intervals can present high impedances that some tuners "
              "cannot match. [Original author's explanation](https://copland.udel.edu/~mm/ham/randomWire/indexOld.html). "
              "A deliberate end-fed half-wave with a suitable matching network is a different setup.", "",
              "## Unflagged spans for all selected bands", "",
              "These are gaps in this estimate, above the quarter-wave guide. Endpoints touch flagged "
              "intervals, so they should not be treated as recommended cut lengths. Installation, "
              "wire insulation, counterpoise and matching equipment affect actual behaviour. "
              "Optional padding shrinks these spans but does not model those effects.", "",
              "| Feet | Metres |", "|---|---|"]
    lines += [f"| {low:.3f}–{high:.3f} | {low * FT_TO_M:.3f}–{high * FT_TO_M:.3f} |" for low, high in gaps]
    if not gaps:
        lines += ["", "No unflagged spans remain within this display."]
    lines += ["", "## Half-wave intervals", "",
              "Values below exclude optional padding. A † marks an interval clipped at the display limit.", "",
              "| Band | Multiple | Feet | Metres |", "|---|---|---|---|"]
    lines += [f"| {r['band_m']} m | {r['multiple']}×{' †' if r['clipped_at_plot_limit'] else ''} | "
              f"{r['low_ft']:.3f}–{r['high_ft']:.3f} | {r['low_m']:.3f}–{r['high_m']:.3f} |" for r in records]
    lines += ["", "[Full-precision calculation data](" + stem.with_suffix(".json").name + ")", ""]
    stem.with_suffix(".md").write_text("\n".join(lines))


def finite_positive(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def finite_nonnegative(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="core",
                        help="core: 40/30/20 m (default); hf: 40 through 10 m")
    parser.add_argument("--bands", nargs="+", choices=BANDS,
                        help="custom selection, e.g. --bands 40 20 17")
    parser.add_argument("--include-80", action="store_true", help="add occasional 80 m use")
    parser.add_argument("--unit", choices=("ft", "m"), default="ft", help="main axis and input units")
    parser.add_argument("--max-length", type=finite_positive,
                        help="plot maximum in --unit; defaults to 135 ft or 45 m")
    parser.add_argument("--padding", type=finite_nonnegative, default=0,
                        help="expand each half-wave interval on both sides in --unit (default: 0)")
    parser.add_argument("--output", type=Path, help="output filename stem, without an extension")
    args = parser.parse_args()
    chosen = set(args.bands or PROFILES[args.profile])
    if args.include_80:
        chosen.add("80")
    bands = [band for name, band in BANDS.items() if name in chosen]
    max_length = args.max_length if args.max_length is not None else (45 if args.unit == "m" else 135)
    max_ft = max_length / FT_TO_M if args.unit == "m" else max_length
    padding_ft = args.padding / FT_TO_M if args.unit == "m" else args.padding
    if max_ft > 10000 or padding_ft > max_ft:
        parser.error("maximum must be at most 10,000 ft and padding must not exceed the maximum")
    suffix = "-".join(b.name for b in bands) if args.bands else args.profile + ("-80" if args.include_80 else "")
    stem = args.output or Path(__file__).resolve().parent / "plots" / f"random-wire-{suffix}"
    if stem.suffix:
        parser.error("--output must be a filename stem without an extension")
    stem.parent.mkdir(parents=True, exist_ok=True)
    make_plot(bands, max_ft, padding_ft, args.unit, stem.with_suffix(".png"))
    write_report(bands, max_ft, padding_ft, stem)
    for extension in (".png", ".md", ".json"):
        print(stem.with_suffix(extension))


if __name__ == "__main__":
    main()
