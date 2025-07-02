#!/bin/bash

# Configuration
SIZES=("1K" "100K" "1M" "100M" "1G" "10G" "25G" "50G" "100G")
FILE_COUNTS=(1 10 50 100 500 1000 5000)
MAX_SZ=500
MAX_TOTAL_SIZE=$(($MAX_SZ * 1024 * 1024 * 1024)) 
BENCHMARK_SCRIPT="./bench5.sh"
LOG_DIR="./logs"
mkdir -p "$LOG_DIR"

# Ensure benchmark script is executable
if [[ ! -x "$BENCHMARK_SCRIPT" ]]; then
    echo "Error: $BENCHMARK_SCRIPT is not executable."
    exit 1
fi

# Convert sizes like 1K, 100M to bytes
size_to_bytes() {
    numfmt --from=iec <<< "$1"
}

# Loop over size and count combinations
for size in "${SIZES[@]}"; do
    size_bytes=$(size_to_bytes "$size")
    for count in "${FILE_COUNTS[@]}"; do
        total_size=$((size_bytes * count))
        if (( total_size > MAX_TOTAL_SIZE )); then
            echo "Skipping $count files of size $size (total size > ${MAX_SZ}GB)"
            break
        fi

        echo "=============================================="
        echo "Running benchmark for size=$size, count=$count"
        echo "=============================================="

        # Run and save output
        sbatch "$BENCHMARK_SCRIPT" "$size" "$count"
    done
done

echo "All benchmarks complete. Logs saved to $LOG_DIR/"
