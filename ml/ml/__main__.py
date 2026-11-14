"""CLI: python -m ml prepare [orders|tweets] | train risk|text ... | evaluate risk|text ... | export-evals"""

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
    commands.add_parser("export-evals", help="write artifacts/eval/*.json comparison tables for the app")
    return parser.parse_args()


def export_evals():
    """Collect the comparison tables the Models page shows into artifacts/eval/<kind>.json."""
    import json

    from ml.data import artifacts_dir

    root = artifacts_dir()
    read = lambda path: json.loads(path.read_text())
    risk = read(root / "risk/v1/metrics.json")
    tables = {
        "risk_models": {model: {split: risk[split][model] for split in risk} for model in risk["val"]},
        "incident_models": {path.name.split("-", 1)[1]: read(path / "metrics.json") for path in root.glob("text/v1-*")},
        "incident_folds": {path.stem: read(path) for path in [*root.glob("text/loeo-*.json"), root / "text/cascade.json"]},
    }
    (root / "eval").mkdir(exist_ok=True)
    for kind, table in tables.items():
        (root / "eval" / f"{kind}.json").write_text(json.dumps(table, indent=2))
        print(f"eval/{kind}.json: {len(table)} rows")


def main():
    args = parse_args()
    if args.command == "export-evals":
        export_evals()
    elif args.command == "prepare":
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
