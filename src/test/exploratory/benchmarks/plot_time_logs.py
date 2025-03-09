#!/usr/bin/env python3
# Copyright (c) 2021-2025 José Manuel Barroso Galindo <theypsilon@gmail.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# You can download the latest version of this tool from:
# https://github.com/MiSTer-devel/Downloader_MiSTer

import re
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from scipy.stats import iqr
from pathlib import Path

from src.debug import chdir_root
from src.test.exploratory.benchmarks.time_multiple_runs import percent_faster


def parse_times(log_path):
    log_data = open(log_path, 'r').read()

    run_seconds = []
    launcher_seconds = []

    seconds_pattern = re.compile(r'\[\d+\s+(run|launcher)\]\s+([\d\.]+) seconds')

    for line in log_data.split('\n'):
        match = seconds_pattern.search(line)
        if match:
            type_ = match.group(1)
            seconds = float(match.group(2))

            if type_ == 'run':
                run_seconds.append(seconds)
            elif type_ == 'launcher':
                launcher_seconds.append(seconds)

    print("Run iterations:", len(run_seconds))
    print("Launcher iterations:", len(launcher_seconds))
    print()
    return np.array(run_seconds), np.array(launcher_seconds)


def plot_data(ax, data, color, label, outliers, y_max, y_min):
    non_outliers = [x for x in data if x not in outliers]
    indices = [i for i, x in enumerate(data) if x not in outliers]

    ax.scatter(indices, non_outliers, label=f'{label}', color=color)
    ax.plot(indices, non_outliers, color=color)

    for i, val in enumerate(data):
        if val in outliers:
            ax.scatter(i, y_max if val > y_max else y_min, color=color, marker='|', s=100, linewidths=2)

    return non_outliers


def main(log_path):
    improved_arr, baseline_arr = parse_times(log_path)

    mean_improved = np.mean(improved_arr)
    std_improved = np.std(improved_arr, ddof=1)  # 'ddof=1' for sample standard deviation

    print("Mean (improved program):", mean_improved)
    print("Std Dev (improved program):", std_improved)
    print()

    mean_baseline = np.mean(baseline_arr)
    std_baseline = np.std(baseline_arr, ddof=1)  # 'ddof=1' for sample standard deviation

    print("Mean (baseline program):", mean_baseline)
    print("Std Dev (baseline program):", std_baseline)
    print()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    fig.canvas.manager.set_window_title(Path(log_path).name)

    ax1.hist(improved_arr, bins=20, alpha=0.5, label='Improved')
    ax1.hist(baseline_arr, bins=20, alpha=0.5, label='Baseline')
    ax1.set_xlabel('Execution Time')
    ax1.set_ylabel('Frequency')
    ax1.set_title(f'Distribution of Execution Times ({len(improved_arr)} Improved & {len(baseline_arr)} Baseline)')
    ax1.legend()

    raw_avg_improved = improved_arr.mean()
    raw_avg_baseline = baseline_arr.mean()

    indices = np.arange(len(improved_arr))

    if False:  # Correcting for performance degradation over time
        degradation_improved = np.polyval(np.polyfit(indices, improved_arr, 1), indices) - raw_avg_improved
        degradation_baseline = np.polyval(np.polyfit(indices, baseline_arr, 1), indices) - raw_avg_baseline

        improved_arr = improved_arr - degradation_improved
        baseline_arr = baseline_arr - degradation_baseline

    regression_improved = np.polyval(np.polyfit(indices, improved_arr, 1), indices)
    regression_baseline = np.polyval(np.polyfit(indices, baseline_arr, 1), indices)

    outliers_threshold = 4

    valid_improved = improved_arr[np.abs(improved_arr - np.median(improved_arr)) <= outliers_threshold * iqr(improved_arr)]
    outliers_improved = improved_arr[np.abs(improved_arr - np.median(improved_arr)) > outliers_threshold * iqr(improved_arr)]

    valid_baseline = baseline_arr[np.abs(baseline_arr - np.median(baseline_arr)) <= outliers_threshold * iqr(baseline_arr)]
    outliers_baseline = baseline_arr[np.abs(baseline_arr - np.median(baseline_arr)) > outliers_threshold * iqr(baseline_arr)]

    avg_improved = valid_improved.mean()
    avg_baseline = valid_baseline.mean()

    print(f'Improvement: {percent_faster(avg_improved, avg_baseline)}%')
    print(f'Improved Outliers:', outliers_improved)
    print(f'Baseline Outliers:', outliers_baseline)
    print(f'Improvement with outliers: {percent_faster(raw_avg_improved, raw_avg_baseline)}%')

    y_max, y_min = max(max(valid_improved), max(valid_baseline)), min(min(valid_improved), min(valid_baseline))
    tick_distance_y = int((y_max - y_min) // 150) * 5 if (y_max - y_min) >= 150 else 5
    y_max, y_min = y_max + tick_distance_y - y_max % tick_distance_y, y_min - y_min % tick_distance_y

    plot_data(ax2, improved_arr, 'blue', 'Improved', outliers_improved, y_max, y_min)
    plot_data(ax2, baseline_arr, 'red', 'Baseline', outliers_baseline, y_max, y_min)
    ax2.plot(indices, regression_improved, color='blue', linestyle='--', label=f'Average Improved: {avg_improved:.3f}')
    ax2.plot(indices, regression_baseline, color='red', linestyle='--', label=f'Average Baseline: {avg_baseline:.3f}')
    for i in range(int(y_min), int(y_max), tick_distance_y):
        ax2.axhline(y=i, color='black', linestyle=':', linewidth=0.5)

    ax2.set_xlabel('Iteration')
    ax2.set_ylabel('Time (seconds)')
    ax2.set_title('Improved vs Baseline')
    ax2.set_ylim(y_min, y_max)
    ax2.set_yticks(list(range(int(y_min), int(y_max) + 1, tick_distance_y)))
    ax2.legend()

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    chdir_root()
    main(sys.argv[1] if len(sys.argv) > 1 else 'downloader.times.log')
