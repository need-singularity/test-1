# tecs/data/__main__.py
"""Entry-point for ``python -m tecs.data.data_manager``.

Usage::

    python -m tecs.data.data_manager --download
"""
import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tecs.data.data_manager",
        description="TECS data manager CLI",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download ConceptNet and WordNet data to the cache directory.",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/",
        metavar="DIR",
        help="Directory for cached data (default: data/).",
    )
    args = parser.parse_args(argv)

    if args.download:
        from tecs.data.data_manager import DataManager

        dm = DataManager(cache_dir=args.cache_dir, use_external=True)
        dm.download_external()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
