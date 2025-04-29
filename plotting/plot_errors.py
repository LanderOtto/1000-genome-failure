import argparse
import json

import matplotlib.pyplot as plt
import pandas as pd
import plotly.io as pio
import plotly.express as px
from datetime import datetime, timedelta


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

    # data = [
    #     {"time": v["time"], "job": k, "error_type": v["error_type"]}
    #     for k, values in combined_results.items()
    #     for v in values
    #     if v["status"] == "ERROR"
    # ]
    # data = sorted(
    #     [
    #         {"time": v["time"], "job": k, "error_type": v["error_type"]}
    #         for k, values in combined_results.items()
    #         for v in values
    #         if v["status"] == "ERROR"
    #     ],
    #     key=lambda x: x["job"],
    # )
    data = [
        {"time": v["time"], "job": k, "error_type": v.get("error_type", None)}
        for k, values in timeline.items()
        for v in values
    ]
    df = pd.DataFrame(data)
    start_date = pd.Timestamp("2024-01-01")
    df["time"] = start_date + df["time"]
    df["time"] = (df["time"] - start_date).dt.total_seconds()

    # job_order = sorted(df["job"].unique())
    job_order = df.groupby("job")["time"].min().sort_values().index.tolist()

    # Create scatter plot
    fig = px.scatter(
        df,
        x="time",
        y="job",
        color="error_type",
        symbol="error_type",
        title="Errors Over Time by Job",
        labels={"time": "Timestamp", "job": "Job", "error_type": "Error Type"},
        category_orders={"job": job_order},
    )
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Job",
        legend_title="Error Occurred During",
        height=400,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(
            x=0.7,  # Horizontal position (0 = far left, 1 = far right)
            y=0.9,  # Vertical position (0 = bottom, 1 = top)
            traceorder="normal",
            bgcolor="rgba(255, 255, 255, 0.5)",  # Background color (optional)
            bordercolor="Black",  # Border color (optional)
            borderwidth=1,  # Border width (optional)
        ),
    )
    fig.write_image("errors_over_time_by_job.pdf")
    fig.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("timeline", help="Timeline file")
    main(parser.parse_args())
