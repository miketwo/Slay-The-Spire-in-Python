#!/usr/bin/env python3
from argparse import ArgumentParser

from game import main

if __name__ == '__main__':
    args = ArgumentParser(description="Run a game of Slay the Spire")
    args.add_argument('-s', '--seed', type=int, help="Seed to use for the game", default=None)
    main(seed=args.parse_args().seed)
