import argparse
import json
import os
from datetime import timedelta
from pathlib import PurePath

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


def save_plot_with_prefix(prefix, format_="png", directory="."):
    os.makedirs(directory, exist_ok=True)
    existing_files = [
        f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith(format_)
    ]
    count = len(existing_files)
    filename = f"{prefix}_{count + 1}.{format_}"
    filepath = os.path.join(directory, filename)
    plt.savefig(filepath)
    print(f"Plot saved as {filepath}")


def str_to_timedelta(time_str):
    h, m, s = time_str.split(":")
    return timedelta(hours=int(h), minutes=int(m), seconds=float(s))


def deserialize_jobs(jobs):
    return {
        k: [
            {v1: (str_to_timedelta(v2) if v1 == "time" else v2) for v1, v2 in v.items()}
            for v in values
        ]
        for k, values in jobs.items()
    }


def main(args):
    with open(args.timeline) as fd:
        timeline = deserialize_jobs(json.load(fd))

    from_error_to_recovery_status = {}

    tasks = []
    error_points = []  # (job_name, time, error_type)
    locations = {}

    start_wf = None
    end_wf = None

    start_time = None
    last_status = None
    for job_name, events in timeline.items():
        if (
            "-injector" in job_name
            or "-collector" in job_name
            or "get_interval" in job_name
            or "get_chromosome" in job_name
        ):
            continue

        for event in events:
            status = event["status"]

            if start_wf is None or event["time"] < start_wf:
                start_wf = event["time"]
            elif end_wf is None or event["time"] > end_wf:
                end_wf = event["time"]

            if status == "ERROR":
                from_error_to_recovery_status.setdefault(job_name, []).append(
                    {"error_timestamp": event["time"], "start_recovery_timestamp": None}
                )
            elif status == "ROLLBACK":
                if job_name in from_error_to_recovery_status.keys():
                    from_error_to_recovery_status[job_name][-1][
                        "start_recovery_timestamp"
                    ] = event["time"]
                else:
                    print("Request rollback of a step which terminate correctly")

            if status == "ALLOCATED":
                if event["location"] not in locations.keys():
                    locations[event["location"]] = f"image{len(locations)}"
                location = locations[event["location"]]

            elif status == "RUNNING" and (
                start_time is None or last_status == "ALLOCATED"
            ):
                start_time = event["time"]
            elif status in {"COMPLETED", "ERROR"} and last_status == "RUNNING":
                tasks.append(
                    (job_name, start_time, event["time"] - start_time, status, location)
                )
                start_time = None
            elif status == "ROLLBACK" and (last_status in ("COMPLETED", "RECOVERY")):
                # COMPLETED -> ROLLBACK: re-execute a completed job
                # RECOVERY -> ROLLBACK: re-execute a failed job
                pass
            elif status == "RECOVERY" and last_status == "ERROR":
                # ERROR -> RECOVERY: re-execute a failed job
                pass
            elif status == "ERROR" and last_status == "RECOVERY":
                # RECOVERY -> ERROR: error scheduling
                pass
            elif last_status == "ALLOCATED" and status == "ERROR":
                error_type = event.get("error_type", "unknown")
                print(
                    f"WARNING: job {job_name} from {last_status} to {status}: err: {error_type} "
                )
            elif last_status == "ALLOCATED" and status == "RUNNING":
                print(f"WARNING: job {job_name} from {last_status} to {status} ")
            elif last_status == "RECOVERY" and status == "RUNNING":
                print(f"WARNING: job {job_name} from {last_status} to {status} ")
            elif last_status == "RECOVERY" and status == "COMPLETED":
                print(f"WARNING: job {job_name} from {last_status} to {status} ")
            elif last_status == "ALLOCATED" and status == "COMPLETED":
                print(f"WARNING: job {job_name} from {last_status} to {status} ")
            else:
                raise ValueError(f"Unknown event status: {last_status} -> {status}")
            if status == "ERROR":
                error_type = event.get("error_type", "unknown")
                error_points.append((job_name, event["time"], error_type))
            last_status = status

    per_step = {}
    for j, fails in from_error_to_recovery_status.items():
        for recovery_times in fails:
            print(
                f"Job {j} time to analyze rollback: {recovery_times['start_recovery_timestamp'] - recovery_times['error_timestamp']}"
            )
            step = os.path.dirname(j)
            per_step.setdefault(step, []).append(
                (
                    recovery_times["start_recovery_timestamp"]
                    - recovery_times["error_timestamp"]
                ).total_seconds()
            )
    total_times = [
        (
            recovery_times["start_recovery_timestamp"]
            - recovery_times["error_timestamp"]
        ).total_seconds()
        for _, fails in from_error_to_recovery_status.items()
        for recovery_times in fails
    ]

    # remove delay time
    total_times = [e - 5 for e in total_times]
    for ts in per_step.values():
        for i in range(len(ts)):
            ts[i] -= 5

    import statistics

    def metrics(data):
        maximum = max(data)
        minimum = min(data)
        average = statistics.mean(data)
        stddev = statistics.stdev(data)  # For sample stddev; use pstdev for population
        median = statistics.median(data)
        if average != 0:
            stddev_percent = (stddev / average) * 100
        else:
            stddev_percent = float("inf")  # Avoid division by zero

        # Output
        print(f"Max: {maximum}")
        print(f"Min: {minimum}")
        print(f"Average: {average}")
        print(f"Standard Deviation: {stddev}")
        print(f"Standard Deviation (% of Average): {stddev_percent:.2f}%")
        print(f"Median: {median}")

    print("Tempi totali")
    metrics(total_times)
    print()

    for s, ts in per_step.items():
        print(f"Tempo per step {s}")
        if len(ts) > 1:
            metrics(ts)
        else:
            print("single time point", ts)
        print()

    labels = [os.path.basename(k) for k, v in per_step.items()]
    data = [v for v in per_step.values()]  # [per_step[step] for step in labels]

    # labels.append("total")
    # data.append(total_times)

    # Create boxplot
    # plt.boxplot(data, labels=labels, patch_artist=True)
    # plt.title("Latency from Error Occurrence to Recovery Evaluation per Step")
    # plt.ylabel("Time (seconds)")
    # plt.xlabel("Step")
    # plt.grid(True)

    # # Show plot
    # plt.savefig("latency_evaluation.pdf", format="pdf", bbox_inches="tight")
    # plt.show()

    import numpy as np

    positions = np.arange(1, len(data) + 1)

    bar_values = [np.average(d) for d in data]

    step_colors = {
        "individuals": "skyblue",
        "individuals_merge": "violet",
        "mutation_overlap": "lightgreen",
        "frequency": "salmon",
    }
    bar_colors = [step_colors[label] for label in labels]

    # plt.figure(figsize=(8, 6))

    # plt.boxplot(data, labels=labels, patch_artist=True)

    # bar_width = 0.5
    # plt.bar(positions, bar_values, width=bar_width, color=bar_colors, alpha=0.5, label='Average latency')

    # plt.title("Latency from Error Occurrence to Recovery Evaluation per Step")
    # plt.ylabel("Time (seconds)")
    # plt.xlabel("Step")
    # plt.grid(True)
    # plt.legend()

    fig, ax = plt.subplots(figsize=(8, 6))

    # box = ax.boxplot(data, labels=labels, patch_artist=True)
    # for patch, label in zip(box['boxes'], labels):
    #     patch.set_facecolor(step_colors[label])
    #     # patch.set_alpha(0.5)  # Optional: match transparency with bars

    # Boxplot with patch_artist=True for coloring boxes
    box = ax.boxplot(
        data, labels=labels, patch_artist=True, medianprops=dict(linewidth=2)
    )

    # Color boxes and median lines, increase stroke width for boxplot lines
    for patch, median_line, label in zip(box["boxes"], box["medians"], labels):
        color = step_colors[label]

        # Color box fill
        patch.set_facecolor(color)
        # patch.set_alpha(0.5)

        # Color median line and increase linewidth
        median_line.set_color("black")
        median_line.set_linewidth(3)

    # Increase linewidth of boxplot edges (boxes, whiskers, caps)
    for element_name in ["boxes", "whiskers", "caps"]:
        for line in box[element_name]:
            line.set_linewidth(2)

    bar_width = 0.5
    ax.bar(
        positions,
        bar_values,
        width=bar_width,
        color=bar_colors,
        alpha=0.5,
        label=[f"Average latency on {t} failures" for t in labels],
    )
    ax.set_title("Latency from Error Occurrence to Recovery Evaluation per Step")
    ax.set_ylabel("Time (seconds)")
    ax.set_xlabel("Step")
    ax.grid(True)
    ax.legend()

    # Save and show
    plt.savefig("latency_evaluation.pdf", format="pdf", bbox_inches="tight")
    plt.show()

    print(start_wf, end_wf)
    print(f"Workflow time: {(end_wf).total_seconds()}")
    total = 0
    for job_name, start_time, duration, status, location in tasks:
        total += duration.total_seconds()
    print(f"time to compute", total)
    recover_with_delay = sum([t + 5 for t in total_times])
    recover_without = sum(total_times)
    print(
        f"time to analyze necessary action to recover (with delay)",
        recover_with_delay,
        f"{recover_with_delay / (total +recover_with_delay) *  100:.2f}%",
    )
    print(
        f"time to analyze necessary action to recover (without)",
        recover_without,
        f"{recover_without / (recover_without + total)*  100:.2f}%",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", help="Timeline file")
    main(parser.parse_args())
