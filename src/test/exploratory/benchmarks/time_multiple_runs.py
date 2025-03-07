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

import sys
import time
import random
import subprocess
import traceback
from datetime import datetime
import os
from subprocess import CalledProcessError
from src.debug import exec_ssh, operations_dict, chdir_root


def main(operation, iterations, target):
    log(f'[BEGIN] Time {iterations} runs of operation "{operation}" on target folder {target}.')

    sample_res, control_res = [], []
    try:
        for op, results in distribute(operation, iterations, sample_res, control_res): iterate(op, target, results)
    except: log(traceback.format_exc())

    log_results('Samples', sample_res)
    log_results('Controls', control_res, sample_res)
    log('[END] Done.')


def iterate(op, target, results):
    if os.path.exists('stop'): raise Exception('stop iterations')
    if target == 'delme': exec_ssh('cd /media/fat; rm -rf delme > /dev/null 2>&1 || true; mkdir -p delme')
    cur_i = len(results) + 1
    log_file = f'/media/fat/time_test_downloader_{cur_i:0>2}_{op}.log'

    before = time.time()
    try:
        operations_dict(env={
            'DEBUG': 'false', 'FAIL_ON_FILE_ERROR': 'true', 'LOGFILE': log_file,
            'ALLOW_REBOOT': '0', 'UPDATE_LINUX': 'false',
        }, retries=False)[op]()
    except CalledProcessError: log(f'[{cur_i:0>2} {op:>8}] ERRORED! See {log_file} for details.')
    duration = time.time() - before

    results.append(duration)
    log(f'[{cur_i:0>2} {op:>8}] {duration:.3f} seconds ({files_in(target)} files)')
    return duration


def log_results(label, results, comp_res=None):
    if len(results) == 0: return

    avg, mean, outliers = average(results)
    avg_faster, mean_faster = '', ''
    if comp_res is not None and len(comp_res) > 0:
        avg_comp, mean_comp, _ = average(comp_res)
        avg_faster, mean_faster = f' (Other is {percent_faster(avg_comp, avg)})', f' ({percent_faster(mean_comp, mean)})'

    log(f'[END] {label} Average: {avg:.3f} seconds{avg_faster}')
    if len(outliers): log(f'[END] {label} Mean: {mean}{mean_faster}, Outliers: {outliers}')


def log(msg):
    now = datetime.now()
    print(f'\nBENCH LOG: {now} {msg}\n')
    with open('downloader.times.log', 'a') as f: f.write(f'{now} {msg}\n')


def distribute(op, iterations, samples, controls):
    if op == 'control': return shuffled_list(iterations, ('run', samples), ('launcher', controls))
    else: return [(op, samples)] * iterations


def shuffled_list(n, x, y, slice_size=7):
    arr = [x, y] * n
    for i in range(n * 2 // slice_size):
        start, end = i * slice_size + 1, (i + 1) * slice_size - 1
        a, b = random.sample(range(start, end), 2)
        arr[a], arr[b] = arr[b], arr[a]
    return arr


def percent_faster(sample, control):
    percent = (control / sample - 1) * 100
    return f'{"+" if percent > 0 else ""}{percent:.2f}%'


def files_in(path):
    return int(exec_ssh(f"find /media/fat/{path} -type f | wc -l", out=subprocess.PIPE).stdout.decode().strip())


def average(results, threshold=4):
    def median(data): return sorted(data)[len(data) // 2]
    def mean(data): return sum(data) / len(data)
    def standard_deviation(data): return (sum((x - mean(data)) ** 2 for x in data) / len(data)) ** 0.5

    prefiltered = [x for x in results if (median(results) / threshold) <= x <= (median(results) * threshold)]
    mean_value = mean(prefiltered)
    std_dev = standard_deviation(prefiltered)
    filtered = [x for x in prefiltered if (mean_value - threshold * std_dev) <= x <= (mean_value + threshold * std_dev)]
    results_outliers, prefiltered_outliers = set(results) - set(prefiltered), set(prefiltered) - set(filtered)
    return mean(filtered), mean_value, list(results_outliers | prefiltered_outliers)


if __name__ == '__main__':
    chdir_root()
    main(
        sys.argv[1].strip().lower() if len(sys.argv) > 1 else 'run',
        int(sys.argv[2]) if len(sys.argv) > 2 else 20,
        sys.argv[3].strip().lower() if len(sys.argv) > 3 else 'delme'
    )
