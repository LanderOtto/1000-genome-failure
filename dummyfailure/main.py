import argparse
import hashlib
import os
import random
import shutil
from pathlib import Path, PurePath


def checksum(path):
    if not Path(path).is_file():
        raise Exception(f"File {path} does not exist.")
    with open(path, "rb") as f:
        sha1_checksum = hashlib.new("sha1", usedforsecurity=False)
        while data := f.read(2**16):
            sha1_checksum.update(data)
        return sha1_checksum.hexdigest()


def main(args):
    if args.context == "individuals":
        content = checksum(args.input_file)
        out_name = f"chr{args.chromosome}n-{args.counter}-{args.stop}.tar.gz"
        size = 200 * 1024 * 1024
    elif args.context == "individuals_merge":
        content = "\n".join(checksum(filepath) for filepath in args.input_files)
        out_name = f"chr{args.chromosome}n.tar.gz"
        size = 200 * 1024 * 1024
    elif args.context == "sifting":
        content = checksum(args.input_file)
        out_name = f"sifted.SIFT.chr{args.chromosome}.txt"
        size = 1.6 * 1024 * 1024
    elif args.context == "frequency":
        content = checksum(f"chr{args.chromosome}n.tar.gz")
        out_name = f"chr{args.chromosome}-{args.population}-freq.tar.gz"
        size = 1 * 1024 * 1024
    elif args.context == "mutation_overlap":
        content = checksum(f"chr{args.chromosome}n.tar.gz")
        out_name = f"chr{args.chromosome}-{args.population}.tar.gz"
        size = 200 * 1024
    else:
        raise ValueError(f"Unknown context: {args.context}")
    if PurePath(out_name).stem == "tar.gz":
        mode_ = "wb"
    else:
        mode_ = "w"
    with open(out_name, mode_) as fd:
        fd.write(content)
        for _ in range(int(size - fd.tell())):
            fd.write("0")

    if not (
        0
        <= (failure_probability := float(os.environ.get("DUMMYFAILURE_PROBABILITY", 0)))
        <= 1
    ):
        raise ValueError(
            f"Failure probability must be between 0 and 1. Got: {failure_probability}"
        )

    if random.random() < failure_probability:
        print(f"Workdir will be deleted: {os.path.dirname(os.getcwd())}")
        shutil.rmtree(os.path.dirname(os.getcwd()))
        raise Exception("Dummy failure raised an exception")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    subparsers = parser.add_subparsers(dest="context")

    # individuals
    individuals_parser = subparsers.add_parser("individuals", help="")
    individuals_parser.add_argument("input_file", type=str)
    individuals_parser.add_argument("chromosome", type=int)
    individuals_parser.add_argument("counter", type=int)
    individuals_parser.add_argument("stop", type=int)
    individuals_parser.add_argument("total", type=int)

    # individuals_merge
    individuals_merge_parser = subparsers.add_parser("individuals_merge", help="")
    individuals_merge_parser.add_argument("chromosome", type=int)
    individuals_merge_parser.add_argument("input_files", nargs="+")

    # sifting
    sifting_parser = subparsers.add_parser("sifting", help="")
    sifting_parser.add_argument("input_file", type=str)
    sifting_parser.add_argument("chromosome", type=str)

    # frequency
    frequency_parser = subparsers.add_parser("frequency", help="")
    frequency_parser.add_argument("-c", "--chromosome", type=int)
    frequency_parser.add_argument("-pop", "--population", type=str)

    # mutation_overlap
    mutation_overlap_parser = subparsers.add_parser("mutation_overlap", help="")
    mutation_overlap_parser.add_argument("-c", "--chromosome", type=int)
    mutation_overlap_parser.add_argument("-pop", "--population", type=str)

    main(parser.parse_args())
