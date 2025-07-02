import argparse
import json
import re
from datetime import datetime


def serialize_jobs(jobs):
    return {
        k: [{v1: str(v2) for v1, v2 in v.items()} for v in values]
        for k, values in jobs.items()
    }


def find_nearest_error(failure_time_dt, error_list):
    nearest_error = None
    nearest_time = None
    min_diff = float("inf")
    for error in error_list:
        if (
            time_diff := abs((failure_time_dt - error["time"]).total_seconds())
        ) < min_diff:
            min_diff = time_diff
            nearest_error = error
            nearest_time = error["time"]
    return nearest_time, nearest_error


def main(args):

    start_executing = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) INFO +EXECUTING step (\/[^\s]+) \(job ([^\)]+)\) on location ([^\s]+) into directory ([^\s:]+):$"
    )

    # Status
    pattern_status = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\sDEBUG\s+Job ([^\s]+) changed status to ([A-Z]+)$"
    )
    # Handling error
    pattern_handling = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+INFO\s+Handling ([\w]+) failure for job ([^\s]+)(?: on step ([^\s]+))?$"
    )
    # Error
    error_line_pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+ERROR\s+(.+)$"
    )
    failed_job_pattern = re.compile(r"^FAILED Job ([^\s]+) with error:$")
    transfer_error_1_pattern = re.compile(
        r"^Error transferring file ([^\s]+) in location ([^\s]+) to ([^\s]+) in location ([^\s]+)$"
    )
    transfer_error_2_pattern = re.compile(
        r"^Error creating file ([^\s]+) with path ([^\s]+) in locations \[(.*?)\]\.$"
    )
    transfer_error_3_pattern = re.compile(r"^FAILED copy from (.+) to (.+)$")
    transfer_error_4_pattern = re.compile(r"^Job ([^\s]+) has no locations$")
    scheduling_pattern = re.compile("a")
    output_process_1_pattern = re.compile(
        r"^Expected (\S+) token of type (\S+), got (\S+)\.$"
    )
    output_process_2_pattern = re.compile(r"Token (\S+) is not optional")
    output_process_3_pattern = re.compile(r"File (.+) does not exist$")

    allocation_pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+DEBUG\s+Job\s+([^\s]+)\s+allocated\s+(.+)$"
    )
    local_alloc_pattern = re.compile(r"locally$")
    remote_alloc_pattern = re.compile(r"on location\s+(.+)$")

    storage_size_err_pattern = re.compile(
        r"Storage (.+) with (.+) paths cannot have negative size: (.+)$"
    )

    combined = {}
    workflow_start = None
    with open(args.logfile) as fd:
        for line in fd.readlines():
            timestamp, job_name, status, location = None, None, None, None
            if workflow_start is None:
                workflow_start = datetime.strptime(
                    " ".join(line.split(" ")[:2]), "%Y-%m-%d %H:%M:%S.%f"
                )
            if match_ := pattern_status.match(line):
                timestamp, job_name, status = match_.groups()
                timestamp = (
                    datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    - workflow_start
                )
                combined.setdefault(job_name, []).append(
                    {"time": timestamp, "status": status}
                )
            elif match_ := pattern_handling.match(line):
                timestamp, failure_type, job_name, step_name = match_.groups()
                timestamp = (
                    datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    - workflow_start
                )
                combined.setdefault(job_name, []).append(
                    {"time": timestamp, "status": "ERROR", "error_type": error_type}
                )
                error_type = None
            elif match_ := allocation_pattern.match(line):
                timestamp, job_name, allocation = match_.groups()
                if match_ := local_alloc_pattern.match(allocation):
                    location_name = match_.group()
                elif match_ := remote_alloc_pattern.match(allocation):
                    location_name = match_.groups()[0]
                timestamp = (
                    datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    - workflow_start
                )
                combined.setdefault(job_name, []).append(
                    {
                        "time": timestamp,
                        "status": "ALLOCATED",
                        "location": location_name,
                    }
                )
            elif match_ := error_line_pattern.match(line):
                timestamp, error_message = match_.groups()
                timestamp = (
                    datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                    - workflow_start
                )
                if failed_job_pattern.match(error_message):
                    error_type = "executing"
                elif (
                    transfer_error_1_pattern.match(error_message)
                    or transfer_error_2_pattern.match(error_message)
                    or transfer_error_3_pattern.match(error_message)
                    or transfer_error_4_pattern.match(error_message)
                ):
                    error_type = "transferring"
                elif (
                    output_process_1_pattern.match(error_message)
                    or output_process_2_pattern.match(error_message)
                    or output_process_3_pattern.match(error_message)
                ):
                    error_type = "retrieving"
                elif scheduling_pattern.match(error_message):
                    error_type = "initializing"
                elif storage_size_err_pattern.match(error_message):
                    print("Warning: storage size error")
                    error_type = "scheduling"
                elif error_message == "FAILED Workflow execution":
                    print("Warning: failed workflow")
                else:
                    raise Exception(f"Unexpected error: {error_message}")
                # combined.setdefault(job_name, []).append(
                #     {
                #         "time": timestamp,
                #         "status": "ERROR",
                #         "error_type": error_type,
                #     }
                # )
    # print(serialize_jobs(jobs))
    # print(serialize_jobs(failures))
    # print(json.dumps(serialize_jobs(combined), indent=2))
    print(
        "Number of steps",
        len(
            {
                s
                for s in combined.keys()
                if "-injector" not in s and "-collector" not in s
            }
        ),
    )
    with open("timeline.json", "w") as fd:
        json.dump(serialize_jobs(combined), fd, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "logfile", help="StreamFlow logfile of an execution in debug mode"
    )
    main(parser.parse_args())
