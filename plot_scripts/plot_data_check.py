import matplotlib.pyplot as plt
import glob
import re
import os
from collections import defaultdict
import numpy as np
import argparse


def main(args):
    # Data structure: {size: [(num_files, mean_time, stddev_time)]}
    benchmark_data = defaultdict(list)

    # Patterns
    header_pattern = re.compile(r"Generating (\d+) files of size (\w+)...")
    total_time_pattern = re.compile(
        r"TOTAL TIME \(run #\d+\) for \d+ files of size \w+: ([\d.]+) seconds"
    )

    # Process each log file
    for log_path in glob.glob(os.path.join(args.benchmark_dir, "*.out")):
        with open(log_path, "r") as f:
            content = f.read()

        # Extract metadata
        header_match = header_pattern.search(content)
        if not header_match:
            print(f"Skipping {log_path}: no valid header")
            continue

        num_files = int(header_match.group(1))
        file_size = header_match.group(2)

        # Extract run times
        times = [float(t) for t in total_time_pattern.findall(content)]
        if len(times) != 5:
            print(f"Warning: {log_path} has {len(times)} runs (expected 5)")

        mean_time = np.mean(times)
        stddev_time = np.std(times)

        benchmark_data[file_size].append((num_files, mean_time, stddev_time))

    # Plot
    plt.figure(figsize=(10, 6))

    def size_to_bytes(size_str):
        units = {"K": 10**3, "M": 10**6, "G": 10**9}
        match = re.match(r"(\d+)([KMG])", size_str)
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            return number * units[unit]
        return float("inf")

    files_5k = []
    for size, values in sorted(
        benchmark_data.items(), key=lambda x: size_to_bytes(x[0])
    ):
        values.sort()
        x = [v[0] for v in values]
        y = [v[1] for v in values]
        stddev = [v[2] for v in values]

        files_5k.extend(
            (
                {"size": size, "avg_time": v[1], "stddev_time": v[2]}
                for v in values
                if v[0] > 2000
            )
        )

        (line,) = plt.plot(x, y, marker="o", label=f"Size {size}")
        color = line.get_color()
        y_lower = [y[i] - stddev[i] for i in range(len(y))]
        y_upper = [y[i] + stddev[i] for i in range(len(y))]
        plt.fill_between(x, y_lower, y_upper, color=color, alpha=0.2)

    plt.xscale("log")
    plt.xlabel("Number of files (log scale)")
    plt.ylabel("Mean total time (seconds)")
    plt.title("Benchmarking File Existence Check")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("benchmark_test_f_summary_plot.png")
    plt.savefig("benchmark_test_f_summary_plot.pdf")
    plt.show()

    print("checksum times of 5k files", files_5k)

    # Transpose the data: {num_files: [(size_in_bytes, mean_time, stddev_time)]}
    transposed_data = defaultdict(list)

    for size_str, records in benchmark_data.items():
        size_bytes = size_to_bytes(size_str)
        for num_files, mean_time, stddev_time in records:
            transposed_data[num_files].append((size_bytes, mean_time, stddev_time))

    # Plot
    plt.figure(figsize=(10, 6))

    for num_files, records in sorted(transposed_data.items()):
        records.sort()
        x = [r[0] for r in records]  # Sizes in bytes
        y = [r[1] for r in records]  # Mean time
        stddev = [r[2] for r in records]

        (line,) = plt.plot(x, y, marker="o", label=f"{num_files} files")
        color = line.get_color()
        y_lower = [y[i] - stddev[i] for i in range(len(y))]
        y_upper = [y[i] + stddev[i] for i in range(len(y))]
        plt.fill_between(x, y_lower, y_upper, color=color, alpha=0.2)

    x_ticks = dict(
        sorted(
            zip(
                benchmark_data.keys(), [size_to_bytes(k) for k in benchmark_data.keys()]
            ),
            key=lambda x: x[1],
        )
    )

    plt.xscale("log")
    plt.xticks(
        # [10**3, 10**4, 10**5, 10**6, 10**7, 10**8, 10],
        # ["1K", "10K", "100K", "1M", "10M", "100M"]
        list(x_ticks.values()),
        list(x_ticks.keys()),
    )
    plt.xlabel("File size")
    plt.ylabel("Mean total time (seconds)")
    plt.title("Benchmark: Time vs File Size for Varying Number of Files")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend(title="Number of files")
    plt.tight_layout()
    plt.savefig("benchmark_summary_by_size.png")
    plt.savefig("benchmark_summary_by_size.pdf")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark_dir")
    main(parser.parse_args())
