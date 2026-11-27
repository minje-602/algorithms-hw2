"""Compare separate chaining and linear probing probe counts."""

import csv
import math
import random
import sys
from pathlib import Path
from typing import NamedTuple
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.hash_table import HashTable
from src.linear_probing import LinearProbingTable

BUCKET_COUNT = 4093
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
FAILED_PROBE_COUNT = 10_000
SEEDS = tuple(range(20261125, 20261135))
_URL_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


class _Result(NamedTuple):
    target_load_factor: float
    actual_load_factor: float
    chaining_success_measured: float
    chaining_success_theoretical: float
    chaining_failure_measured: float
    chaining_failure_theoretical: float
    probing_success_measured: float
    probing_success_theoretical: float
    probing_failure_measured: float
    probing_failure_theoretical: float


def _random_key(generator: random.Random, index: int) -> str:
    label = "".join(generator.choice(_URL_ALPHABET) for _ in range(12))
    return f"https://{label}.example/{index}"


def _prepare_inputs() -> list[tuple[list[str], list[str]]]:
    maximum_size = round(LOAD_FACTORS[-1] * BUCKET_COUNT)
    seed_inputs = []
    for seed in SEEDS:
        key_generator = random.Random(seed)
        keys = [
            _random_key(key_generator, index)
            for index in range(maximum_size)
        ]

        missing_generator = random.Random(seed + len(SEEDS))
        missing_keys = [
            _random_key(missing_generator, maximum_size + index)
            for index in range(FAILED_PROBE_COUNT)
        ]
        seed_inputs.append((keys, missing_keys))
    return seed_inputs


def measure() -> list[_Result]:
    seed_inputs = _prepare_inputs()
    results = []

    for target_load in LOAD_FACTORS:
        target_size = round(target_load * BUCKET_COUNT)
        actual_load = target_size / BUCKET_COUNT
        chaining_success_total = 0.0
        chaining_failure_total = 0.0
        probing_success_total = 0.0
        probing_failure_total = 0.0

        for keys, missing_keys in seed_inputs:
            chaining = HashTable(bucket_count=BUCKET_COUNT, max_load=None)
            probing = LinearProbingTable(
                bucket_count=BUCKET_COUNT, max_load=None
            )

            for index in range(target_size):
                key = keys[index]
                chaining.put(key, index)
                probing.put(key, index)

            chaining_success_probes = 0
            probing_success_probes = 0
            for index in range(target_size):
                key = keys[index]
                chaining_value, chaining_probes = chaining.find(key)
                probing_value, probing_probes = probing.find(key)
                if chaining_value != index or probing_value != index:
                    raise RuntimeError(f"inserted key was not found: {key}")
                chaining_success_probes += chaining_probes
                probing_success_probes += probing_probes

            chaining_failure_probes = 0
            probing_failure_probes = 0
            for key in missing_keys:
                chaining_value, chaining_probes = chaining.find(key)
                probing_value, probing_probes = probing.find(key)
                if chaining_value is not None or probing_value is not None:
                    raise RuntimeError(f"failed probe unexpectedly matched: {key}")
                chaining_failure_probes += chaining_probes
                probing_failure_probes += probing_probes

            chaining_success_total += chaining_success_probes / target_size
            chaining_failure_total += (
                chaining_failure_probes / FAILED_PROBE_COUNT
            )
            probing_success_total += probing_success_probes / target_size
            probing_failure_total += probing_failure_probes / FAILED_PROBE_COUNT

        seed_count = len(SEEDS)
        results.append(
            _Result(
                target_load,
                actual_load,
                chaining_success_total / seed_count,
                1 + actual_load / 2,
                chaining_failure_total / seed_count,
                actual_load,
                probing_success_total / seed_count,
                (1 + 1 / (1 - actual_load)) / 2,
                probing_failure_total / seed_count,
                (1 + 1 / (1 - actual_load) ** 2) / 2,
            )
        )

    return results


def _write_csv(results: list[_Result], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "target_load_factor",
                "actual_load_factor",
                "chaining_success_measured",
                "chaining_success_theoretical",
                "chaining_failure_measured",
                "chaining_failure_theoretical",
                "probing_success_measured",
                "probing_success_theoretical",
                "probing_failure_measured",
                "probing_failure_theoretical",
            )
        )
        for result in results:
            writer.writerow(f"{value:.6f}" for value in result)


def _write_svg(results: list[_Result], destination: Path) -> None:
    width = 1120
    height = 780
    left = 100
    right = 40
    top = 90
    bottom = 190
    plot_width = width - left - right
    plot_height = height - top - bottom
    minimum = 0.05
    maximum = 100.0
    log_minimum = math.log10(minimum)
    log_range = math.log10(maximum) - log_minimum

    def x_position(load_factor: float) -> float:
        return left + (load_factor - results[0].actual_load_factor) / (
            results[-1].actual_load_factor - results[0].actual_load_factor
        ) * plot_width

    def y_position(value: float) -> float:
        return top + (
            math.log10(maximum) - math.log10(value)
        ) / log_range * plot_height

    series = (
        ("Chaining: success theory", 3, "#1769aa", True),
        ("Chaining: success measured", 2, "#1769aa", False),
        ("Chaining: failure theory", 5, "#c62828", True),
        ("Chaining: failure measured", 4, "#c62828", False),
        ("Linear probing: success theory", 7, "#2e7d32", True),
        ("Linear probing: success measured", 6, "#2e7d32", False),
        ("Linear probing: failure theory", 9, "#7b1fa2", True),
        ("Linear probing: failure measured", 8, "#7b1fa2", False),
    )
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Hash-table probe counts by load factor</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="560" y="34" text-anchor="middle" font-family="sans-serif" font-size="21">Separate chaining vs. linear probing</text>',
        '<text x="560" y="60" text-anchor="middle" font-family="sans-serif" font-size="13">4093 buckets, 10 fixed random seeds, 10,000 unsuccessful searches per seed</text>',
    ]

    y_ticks = (0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100)
    for value in y_ticks:
        y = y_position(value)
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#dddddd"/>'
        )
        lines.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" font-size="12">{value:g}</text>'
        )

    for result in results:
        x = x_position(result.actual_load_factor)
        lines.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{height - bottom}" stroke="#eeeeee"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{height - bottom + 22}" text-anchor="middle" font-family="sans-serif" font-size="12">{result.actual_load_factor:.3f}</text>'
        )

    lines.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#333333"/>',
            f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="#333333"/>',
            f'<text x="{left + plot_width / 2:.2f}" y="{height - bottom + 48}" text-anchor="middle" font-family="sans-serif" font-size="14">Actual load factor α</text>',
            f'<text x="24" y="{top + plot_height / 2:.2f}" transform="rotate(-90 24 {top + plot_height / 2:.2f})" text-anchor="middle" font-family="sans-serif" font-size="14">Average probes (log scale)</text>',
        )
    )

    for _, column, color, is_theory in series:
        points = " ".join(
            f"{x_position(result.actual_load_factor):.2f},{y_position(result[column]):.2f}"
            for result in results
        )
        dash_style = ' stroke-dasharray="7 5"' if is_theory else ""
        lines.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash_style}/>'
        )
        if not is_theory:
            for result in results:
                x = x_position(result.actual_load_factor)
                y = y_position(result[column])
                lines.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}"/>'
                )

    legend_columns = (left, left + 500)
    legend_top = height - bottom + 85
    for index, (label, _, color, is_theory) in enumerate(series):
        column = index // 4
        row = index % 4
        x = legend_columns[column]
        y = legend_top + row * 23
        dash_style = ' stroke-dasharray="7 5"' if is_theory else ""
        lines.append(
            f'<line x1="{x}" y1="{y}" x2="{x + 28}" y2="{y}" stroke="{color}" stroke-width="2"{dash_style}/>'
        )
        if not is_theory:
            lines.append(
                f'<circle cx="{x + 14}" cy="{y}" r="3.5" fill="{color}"/>'
            )
        lines.append(
            f'<text x="{x + 38}" y="{y + 4}" font-family="sans-serif" font-size="12">{escape(label)}</text>'
        )

    lines.append("</svg>")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_table(results: list[_Result]) -> None:
    headings = (
        "α actual",
        "Chain S",
        "Chain S theory",
        "Chain F",
        "Chain F theory",
        "Probe S",
        "Probe S theory",
        "Probe F",
        "Probe F theory",
    )
    print(" | ".join(f"{heading:>14}" for heading in headings))
    print("-+-".join("-" * 14 for _ in headings))
    for result in results:
        print(
            " | ".join(
                f"{value:14.4f}"
                for value in (
                    result.actual_load_factor,
                    result.chaining_success_measured,
                    result.chaining_success_theoretical,
                    result.chaining_failure_measured,
                    result.chaining_failure_theoretical,
                    result.probing_success_measured,
                    result.probing_success_theoretical,
                    result.probing_failure_measured,
                    result.probing_failure_theoretical,
                )
            )
        )


def main() -> None:
    results = measure()
    output_dir = Path(__file__).resolve().parent
    csv_path = output_dir / "compare_results.csv"
    svg_path = output_dir / "compare_results.svg"
    _write_csv(results, csv_path)
    _write_svg(results, svg_path)
    _print_table(results)
    print(f"\nCSV: {csv_path}")
    print(f"SVG: {svg_path}")


if __name__ == "__main__":
    main()
