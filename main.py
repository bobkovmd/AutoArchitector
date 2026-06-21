import argparse
from pathlib import Path
from src.autoarchitector.app import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(Path(args.config), Path(args.output))


if __name__ == "__main__":
    main()
