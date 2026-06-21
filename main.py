import argparse
from pathlib import Path
from src.autoarchitector.app import run
from src.autoarchitector.loaders.config_loader import load_config
from src.autoarchitector.loaders.repo_cloner import clone_repos


def main():
    parser = argparse.ArgumentParser(description="AutoArchitector — architecture diagram pipeline")
    parser.add_argument("--config", required=True, help="Path to sources.yaml")
    parser.add_argument("--output", help="Output directory for artifacts")
    parser.add_argument(
        "--clone-repos",
        action="store_true",
        help="Clone all repositories listed in config before processing",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = load_config(config_path)

    if args.clone_repos:
        clone_repos(config.get("repositories", []))

    if args.output:
        run(config_path, Path(args.output))


if __name__ == "__main__":
    main()
