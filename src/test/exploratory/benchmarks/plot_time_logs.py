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
    data = {
        'improved': {'label': 'Downloader 2.2.1', 'short_label': 'v2.2'},
        'baseline': {'label': 'Downloader 2.1', 'short_label': 'v2.1'}
    }
    times = dict(zip(data, parse_times(log_path)))
    indices = np.arange(len(times['improved']))

    for key, d in data.items():
        d['arr'] = np.array(times[key])

        #degradation = np.polyval(np.polyfit(indices, d['arr'], 1), indices) - d['arr'].mean()
        #d['arr'] = d['arr'] - degradation

        d['mean'], std = d['arr'].mean(), d['arr'].std(ddof=1)
        print(f"Mean ({d['label']}): {d['mean']}\nStd Dev ({d['label']}: {std}\n")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    fig.canvas.manager.set_window_title(Path(log_path).with_suffix('.png').name)

    ax1.hist(data['improved']['arr'], bins=20, alpha=0.5, label=data['improved']['label'], color='blue')
    ax1.hist(data['baseline']['arr'], bins=20, alpha=0.5, label=data['baseline']['label'], color='red')
    ax1.set_xlabel('Execution Time (seconds)')
    ax1.set_ylabel('Frequency')
    ax1.set_title(f'Distribution of Execution Times ({len(data["improved"]["arr"])} {data["improved"]["label"]} runs & {len(data["baseline"]["arr"])} {data["baseline"]["label"]} runs)')
    ax1.legend()

    for d in data.values():
        d['regression'] = np.polyval(np.polyfit(indices, d['arr'], 1), indices)
        mask = np.abs(d['arr'] - np.median(d['arr'])) <= 8 * iqr(d['arr'])
        d['valid'], d['outliers'] = d['arr'][mask], d['arr'][~mask]
        d['avg_valid'] = d['valid'].mean()

    improvement = percent_faster(data['improved']['avg_valid'], data['baseline']['avg_valid'])
    raw_improvement = percent_faster(data['improved']['mean'], data['baseline']['mean'])

    print(f'Improvement: {improvement}%')
    for d in data.values():
        print(f'{d["label"]} Outliers:', d['outliers'])
        print(f'{d["label"]} Mean without Outliers: {(d["valid"]).mean()}')
    print(f'Improvement with outliers: {raw_improvement}%')

    y_max = max(max(data[k]['valid']) for k in data)
    y_min = min(min(data[k]['valid']) for k in data)

    plot_data(ax2, data['improved']['arr'], 'blue', data['improved']['label'], data['improved']['outliers'], y_max, y_min)
    plot_data(ax2, data['baseline']['arr'], 'red', data['baseline']['label'], data['baseline']['outliers'], y_max, y_min)

    ax2.plot(indices, data['improved']['regression'], color='blue', linestyle='--', label=f'Average {data["improved"]["short_label"]}: {data["improved"]["avg_valid"]:.3f}s')
    ax2.plot(indices, data['baseline']['regression'], color='red', linestyle='--', label=f'Average {data["baseline"]["short_label"]}: {data["baseline"]["avg_valid"]:.3f}s')

    ax2.set_xlabel('Iteration')
    ax2.set_ylabel('Time (seconds)')
    ax2.set_title(f'{data["improved"]["label"]} vs {data["baseline"]["label"]}')
    ax2.yaxis.grid(True, linestyle='--', alpha=0.5)
    ax2.xaxis.grid(False)
    ax2.legend()

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    chdir_root()
    main(sys.argv[1] if len(sys.argv) > 1 else 'downloader.times.log')
