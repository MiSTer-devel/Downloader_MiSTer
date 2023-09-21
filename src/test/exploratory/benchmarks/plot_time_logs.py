#!/usr/bin/env python3
# Copyright (c) 2021-2022 José Manuel Barroso Galindo <theypsilon@gmail.com>

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

from src.debug import chdir_root
from src.test.exploratory.benchmarks.time_multiple_runs import average, percent_faster


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

    print("Run seconds:", len(run_seconds))
    print("Launcher seconds:", len(launcher_seconds))
    return run_seconds, launcher_seconds


def plot_data(data, color, label, outliers, y_max, y_min):
    non_outliers = [x for x in data if x not in outliers]
    indices = [i for i, x in enumerate(data) if x not in outliers]

    plt.scatter(indices, non_outliers, label=f'{label}', color=color)
    plt.plot(indices, non_outliers, color=color)

    for i, val in enumerate(data):
        if val in outliers:
            plt.scatter(i, y_max if val > y_max else y_min, color=color, marker='|', s=100, linewidths=2)

    return non_outliers


def main(log_path):
    improved, baseline = parse_times(log_path)

    avg_improved, raw_avg_improved, outliers_improved = average(improved)
    avg_baseline, raw_avg_baseline, outliers_baseline = average(baseline)

    print(f'Improvement: {percent_faster(avg_improved, avg_baseline)}%')

    valid_improved = list(set(improved) - set(outliers_improved))
    valid_baseline = list(set(baseline) - set(outliers_baseline))
    y_max, y_min = max(max(valid_improved), max(valid_baseline)), min(min(valid_improved), min(valid_baseline))
    tick_distance_y = int((y_max - y_min) // 150) * 5 if (y_max - y_min) >= 150 else 5
    y_max, y_min = y_max + tick_distance_y - y_max % tick_distance_y, y_min - y_min % tick_distance_y

    plot_data(improved, 'blue', 'Improved', outliers_improved, y_max, y_min)
    plot_data(baseline, 'red', 'Baseline', outliers_baseline, y_max, y_min)

    plt.axhline(y=avg_improved, color='blue', linestyle='--', label=f'Average Improved: {avg_improved:.3f}')
    plt.axhline(y=avg_baseline, color='red', linestyle='--', label=f'Average Baseline: {avg_baseline:.3f}')
    for i in range(int(y_min), int(y_max), tick_distance_y):
        plt.axhline(y=i, color='black', linestyle=':', linewidth=0.5)

    plt.xlabel('Iteration')
    plt.ylabel('Time (seconds)')
    plt.title('Improved vs Baseline')
    plt.ylim(y_min, y_max)
    plt.yticks(list(range(int(y_min), int(y_max) + 1, tick_distance_y)))
    plt.legend()
    plt.show()


if __name__ == '__main__':
    chdir_root()
    main(sys.argv[1] if len(sys.argv) > 1 else 'downloader.times.log')
