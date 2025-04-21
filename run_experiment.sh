#!/bin/bash

for run in {1..10}; do
    echo "Starting run #$run"

    COMMAND="streamflow run streamflow.yml --outdir /tmp/streamflow --debug"
    LOG_FILE="command_output.log"

    $COMMAND > "$LOG_FILE" 2>&1 &
    CMD_PID=$!

    get_last_line() {
        tail -n 1 "$LOG_FILE"
    }

    last_line=""
    while kill -0 $CMD_PID 2>/dev/null; do
        sleep 60
        new_line=$(get_last_line)
        if [ "$new_line" == "$last_line" ]; then
            echo "Command deadlock. Killing process $CMD_PID."
            kill $CMD_PID
            wait $CMD_PID 2>/dev/null
            break
        fi
        last_line="$new_line"
    done

    wait $CMD_PID
    EXIT_CODE=$?

    i=1
    if [ $EXIT_CODE -eq 0 ]; then
        while [ -e "ft-success$i.out" ]; do
            ((i++))
        done
        echo "Experiment success - Saved to ft-success$i.out"
        mv "$LOG_FILE" "ft-success$i.out"
    else
        while [ -e "ft-failed$i.out" ]; do
            ((i++))
        done
        echo "Experiment failed - Saved to ft-failed$i.out"
        mv "$LOG_FILE" "ft-failed$i.out"
    fi

    rm -rf /tmp/streamflow
    echo "Run #$run completed"
    echo "-------------------------"
done
