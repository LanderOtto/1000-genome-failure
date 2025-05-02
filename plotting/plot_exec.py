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

    tasks = []
    error_points = []  # (job_name, time, error_type)
    locations = {}
    for job_name, events in timeline.items():
        if (
            "-injector" in job_name
            or "-collector" in job_name
            or "get_interval" in job_name
            or "get_chromosome" in job_name
        ):
            continue

        start_time = None
        last_status = None
        for event in events:
            status = event["status"]

            if status == "ALLOCATED":
                if event["location"] not in locations.keys():
                    locations[event["location"]] = f"image{len(locations)}"
                location = locations[event["location"]]

            elif status == "RUNNING" and (start_time is None or last_status == "ALLOCATED"):
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
                print(f"WARNING: job {job_name} from {last_status} to {status}: err: {error_type} ")
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
    # Assign unique y-positions to jobs
    job_to_y = {
        job: i
        for i, job in enumerate(
            sorted(
                set(job for job, _, _, _, _ in tasks).union(
                    job for job, _, _ in error_points
                )
            )
        )
    }

    # Mapping for the plots
    status_colors = {
        "COMPLETED": "green",
        "ERROR": "red",
    }
    error_markers = {
        "executing": "*",
        "transferring": "o",
        "retrieving": "^",
        "unknown": "x",
    }

    hatch_patterns = dict(
        zip(
            locations.values(),
            ["/", "x", "o", "O", ".", "*", "\\", "+", "|", "-"],
        )
    )

    # Collect all used error types to generate legend dynamically
    used_error_types = set(et for _, _, et in error_points)

    # Plot bars
    height = len(job_to_y) * 0.6
    width = 16 / 9 * height
    fontsize = 1 * min(width, height)
    print("image size", width, "x", height)
    fig, ax = plt.subplots(figsize=(width, height))
    bar_height = 0.6
    for job_name, start, duration, status, location in tasks:
        y = job_to_y[job_name]
        color = status_colors[status]
        ax.barh(
            y=y,
            width=duration.total_seconds(),
            left=start.total_seconds(),
            height=bar_height,
            color=color,
            hatch=hatch_patterns[location],
        )

    # Plot error points
    for job_name, time, error_type in error_points:
        y = job_to_y[job_name]
        marker = error_markers.get(error_type, "*")
        ax.plot(
            time.total_seconds(),
            y,
            marker=marker,
            color="black",
            markersize=fontsize,
            label=error_type,
        )
    yticks = list(job_to_y.values())
    ylabels = list(["\n".join(PurePath(j).parts[2:]) for j in job_to_y.keys()])
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=fontsize)
    ax.tick_params(axis="x", labelsize=fontsize)
    ax.set_xlabel("Time (seconds)", fontsize=fontsize)
    ax.grid(True)
    plt.title("Job Execution with Errors", fontsize=fontsize)
    legend_elements = [
        Patch(facecolor="green", label="COMPLETED"),
        Patch(facecolor="red", label="ERROR"),
    ]

    legend_elements.extend(
        Patch(facecolor="white", edgecolor="black", hatch=hatch * 3, label=location)
        for location, hatch in hatch_patterns.items()
    )

    # Add error marker legends
    for etype in sorted(used_error_types):
        marker = error_markers.get(etype, "*")
        legend_elements.append(
            Line2D(
                [0],
                [0],
                marker=marker,
                color="black",
                label=f"Error while job: {etype}",
                linestyle="None",
                markersize=8,
            )
        )

    ax.legend(handles=legend_elements, title="Job status", fontsize=fontsize)
    plt.tight_layout()
    save_plot_with_prefix("myplot")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", help="Timeline file")
    main(parser.parse_args())
