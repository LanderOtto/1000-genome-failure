import argparse
import json

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from datetime import timedelta


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

            if status == "RUNNING" and start_time is None:
                start_time = event["time"]
            elif status in {"COMPLETED", "ERROR"} and last_status == "RUNNING":
                tasks.append((job_name, start_time, event["time"] - start_time, status))
                start_time = None
            elif status == "ROLLBACK" and (last_status in ("COMPLETED", "RECOVERY")):
                # COMPLETED -> ROLLBACK: re-execute a completed job
                # RECOVERY -> ROLLBACK: re-execute a failed job
                pass
            elif status == "RECOVERY" and last_status == "ERROR":
                # ERROR -> RECOVERY: re-execute a failed job
                pass
            elif last_status is None and status == "ERROR":
                error_type = event.get("error_type", "unknown")
                print(
                    f"WARNING: error occurs as first event: {error_type}"
                )
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
                set(job for job, _, _, _ in tasks).union(
                    job for job, _, _ in error_points
                )
            )
        )
    }

    print(error_points)

    # Mapping for the plots
    status_colors = {
        "COMPLETED": "green",
        "ERROR": "red",
    }
    error_markers = {
        "executing": "x",
        "transferring": "o",
        "retrieving": "^",
        "unknown": "*",
    }

    # Collect all used error types to generate legend dynamically
    used_error_types = set(et for _, _, et in error_points)

    # Plot bars
    fig, ax = plt.subplots(figsize=(10, len(job_to_y) * 0.6))
    bar_height = 0.6
    for job_name, start, duration, status in tasks:
        y = job_to_y[job_name]
        color = status_colors[status]
        ax.barh(
            y=y,
            width=duration.total_seconds(),
            left=start.total_seconds(),
            height=bar_height,
            color=color,
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
            markersize=10,
            label=error_type,
        )
    yticks = list(job_to_y.values())
    ylabels = list(job_to_y.keys())
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels)
    ax.set_xlabel("Time (seconds)")
    ax.grid(True)
    plt.title("Job Execution Gantt Chart with Errors")
    legend_elements = [
        Patch(facecolor="green", label="COMPLETED"),
        Patch(facecolor="red", label="ERROR"),
    ]

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

    ax.legend(handles=legend_elements, title="Status & Errors")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", help="Timeline file")
    main(parser.parse_args())
