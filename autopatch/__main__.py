"""Entry point: python -m autopatch [OPTIONS]"""
import argparse
from autopatch.orchestrator import run


def main():
    parser = argparse.ArgumentParser(
        description="Autopatch — Autonomous RTX Remix light visibility solver",
    )
    parser.add_argument(
        "--skip-diagnosis", action="store_true",
        help="Skip diagnostic capture, use existing data",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate all components without patching or launching the game",
    )
    args = parser.parse_args()
    run(skip_diagnosis=args.skip_diagnosis, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
