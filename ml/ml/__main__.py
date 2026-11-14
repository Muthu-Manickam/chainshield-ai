"""CLI: python -m ml prepare [orders|tweets] | train risk|text ... | evaluate risk|text ..."""

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m ml")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="build data/processed/*.parquet")
    prepare.add_argument("dataset", nargs="?", choices=["orders", "tweets"])
    for name in ("train", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("task", choices=["risk", "text"])
        command.add_argument("--version", type=int, required=True)
        command.add_argument("--family", choices=["tfidf", "bilstm", "distilbert"], help="text model family")
    commands.choices["train"].add_argument("--extra", default="", help="risk: extra blocks, e.g. s1,s2")
    commands.choices["train"].add_argument("--extra-labels", help="text: parquet of reviewed labels")
    commands.choices["evaluate"].add_argument("--final", action="store_true", help="score the sealed test set")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "prepare":
        from ml import data

        if args.dataset in (None, "tweets"):
            data.prepare_tweets()
        if args.dataset in (None, "orders"):
            data.prepare_orders()
    elif args.task == "risk":
        from ml import risk

        if args.command == "train":
            risk.train(args.version, tuple(block for block in args.extra.split(",") if block))
        elif args.final:
            risk.evaluate_final(args.version)
        else:
            raise SystemExit("evaluate risk needs --final (validation and S3 metrics are written at training)")
    else:
        from ml import text

        if args.family is None:
            raise SystemExit("text tasks need --family")
        if args.command == "train":
            text.train(args.family, args.version, args.extra_labels)
        else:
            text.evaluate(args.family, args.version, args.final)


if __name__ == "__main__":
    main()
