"""Measure separate-chaining probe counts across hash-table load factors."""

import csv
import math
import random
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hash_table import HashTable

BUCKET_COUNT = 4093
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
FAILED_PROBE_COUNT = 10_000
RANDOM_SEED = 20261125
_URL_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

_Row = tuple[float, float, float, float, float, float]


def _random_url(generator: random.Random, index: int) -> str:
    label = "".join(generator.choice(_URL_ALPHABET) for _ in range(12))
    return f"https://{label}.example/{index}"


def measure() -> list[_Row]:
    generator = random.Random(RANDOM_SEED)
    table = HashTable(bucket_count=BUCKET_COUNT, max_load=None)
    urls: list[str] = []
    results: list[_Row] = []

    for target_load in LOAD_FACTORS:
        target_size = round(target_load * BUCKET_COUNT)
        while len(urls) < target_size:
            url = _random_url(generator, len(urls))
            table.put(url, len(urls))
            urls.append(url)

        actual_load = table.load_factor
        successful_comparisons = 0
        for url in urls:
            value, comparisons = table.find(url)
            if value is None:
                raise RuntimeError(f"inserted URL was not found: {url}")
            successful_comparisons += comparisons

        failed_comparisons = 0
        for index in range(FAILED_PROBE_COUNT):
            url = f"https://missing-{index}.example/not-stored"
            value, comparisons = table.find(url)
            if value is not None:
                raise RuntimeError(f"failed probe unexpectedly matched: {url}")
            failed_comparisons += comparisons

        results.append(
            (
                target_load,
                actual_load,
                successful_comparisons / len(urls),
                1 + actual_load / 2,
                failed_comparisons / FAILED_PROBE_COUNT,
                actual_load,
            )
        )

    return results


def _write_csv(results: list[_Row], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "target_load_factor",
                "actual_load_factor",
                "successful_average_comparisons",
                "successful_theoretical",
                "unsuccessful_average_comparisons",
                "unsuccessful_theoretical",
            )
        )
        for row in results:
            writer.writerow(f"{value:.6f}" for value in row)


def _write_svg(results: list[_Row], destination: Path) -> None:
    width = 1000
    height = 600
    left = 90
    right = 30
    top = 70
    bottom = 80
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = max(max(row[2], row[3], row[4], row[5]) for row in results)
    y_max = max(4.5, math.ceil(maximum * 2) / 2)

    def x_position(load: float) -> float:
        return left + (load - LOAD_FACTORS[0]) / (
            LOAD_FACTORS[-1] - LOAD_FACTORS[0]
        ) * plot_width

    def y_position(value: float) -> float:
        return top + (y_max - value) / y_max * plot_height

    series = (
        ("Successful (measured)", 2, "#1769aa"),
        ("Successful (theory: 1 + α/2)", 3, "#58a6d6"),
        ("Unsuccessful (measured)", 4, "#c62828"),
        ("Unsuccessful (theory: α)", 5, "#ef8a8a"),
    )
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Hash-table probe counts by load factor</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="500" y="32" text-anchor="middle" font-family="sans-serif" font-size="20">Separate-chaining probe experiment</text>',
    ]

    for tick in range(int(y_max * 2) + 1):
        value = tick / 2
        y = y_position(value)
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#dddddd"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 5:.2f}" text-anchor="end" font-family="sans-serif" font-size="12">{value:.1f}</text>'
        )

    x_ticks = (0.25, 1.0, 2.0, 3.0, 4.0)
    for value in x_ticks:
        x = x_position(value)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{height - bottom}" stroke="#eeeeee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{height - bottom + 24}" text-anchor="middle" font-family="sans-serif" font-size="12">{value:g}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#333333"/>',
            f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#333333"/>',
            f'<text x="{left + plot_width / 2:.2f}" y="{height - 20}" text-anchor="middle" font-family="sans-serif" font-size="14">Load factor α</text>',
            f'<text x="22" y="{top + plot_height / 2:.2f}" transform="rotate(-90 22 {top + plot_height / 2:.2f})" text-anchor="middle" font-family="sans-serif" font-size="14">Average nodes compared</text>',
        )
    )

    for label, column, color in series:
        points = " ".join(
            f"{x_position(row[1]):.2f},{y_position(row[column]):.2f}"
            for row in results
        )
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>'
        )
        for row in results:
            x = x_position(row[1])
            y = y_position(row[column])
            lines.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>'
            )

    legend_x = left + 18
    legend_y = top + 18
    for index, (label, _, color) in enumerate(series):
        y = legend_y + index * 20
        lines.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 24}" y2="{y}" stroke="{color}" stroke-width="3"/>'
        )
        lines.append(
            f'<text x="{legend_x + 32}" y="{y + 5}" font-family="sans-serif" font-size="12">{escape(label)}</text>'
        )

    lines.append("</svg>")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_table(results: list[_Row]) -> None:
    headings = (
        "α (actual)",
        "Success measured",
        "Success theory",
        "Failure measured",
        "Failure theory",
    )
    print(" | ".join(f"{heading:>17}" for heading in headings))
    print("-+-".join("-" * 17 for _ in headings))
    for row in results:
        print(
            " | ".join(
                f"{value:17.4f}"
                for value in (row[1], row[2], row[3], row[4], row[5])
            )
        )


def main() -> None:
    results = measure()
    output_dir = Path(__file__).resolve().parent
    csv_path = output_dir / "results.csv"
    svg_path = output_dir / "results.svg"
    _write_csv(results, csv_path)
    _write_svg(results, svg_path)
    _print_table(results)
    print(f"\nCSV: {csv_path}")
    print(f"SVG: {svg_path}")


if __name__ == "__main__":
    main()
