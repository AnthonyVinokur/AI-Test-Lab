from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.datasets import DatasetEntry, DatasetService, DatasetStatus, JsonDatasetRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Test Lab Dataset Management")
    parser.add_argument("--storage", default="datasets", help="Dataset storage directory")

    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a dataset")
    create.add_argument("name")
    create.add_argument("--description", default="")
    create.add_argument("--tag", action="append", default=[])

    list_command = commands.add_parser("list", help="List datasets")
    list_command.add_argument("--status", choices=[item.value for item in DatasetStatus])
    list_command.add_argument("--tag")

    show = commands.add_parser("show", help="Show a dataset or version")
    show.add_argument("dataset_id")
    show.add_argument("--version", type=int)

    add = commands.add_parser("add-entry", help="Add an entry")
    add.add_argument("dataset_id")
    add.add_argument("--name", required=True)
    add.add_argument("--input", required=True)
    add.add_argument("--expected-output")
    add.add_argument("--category", default="general")
    add.add_argument("--tag", action="append", default=[])

    status = commands.add_parser("set-status", help="Change lifecycle status")
    status.add_argument("dataset_id")
    status.add_argument("status", choices=[item.value for item in DatasetStatus])

    rollback = commands.add_parser("rollback", help="Create a new version from an old version")
    rollback.add_argument("dataset_id")
    rollback.add_argument("version", type=int)

    export = commands.add_parser("export", help="Export a version")
    export.add_argument("dataset_id")
    export.add_argument("--version", type=int)
    export.add_argument("--output", type=Path)

    import_command = commands.add_parser("import", help="Import entries from JSON")
    import_command.add_argument("dataset_id")
    import_command.add_argument("input_file", type=Path)
    import_command.add_argument("--replace", action="store_true")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = DatasetService(JsonDatasetRepository(args.storage))

    if args.command == "create":
        dataset = service.create_dataset(
            name=args.name,
            description=args.description,
            tags=args.tag,
            created_by="cli",
        )
        print(dataset.manifest.id)

    elif args.command == "list":
        selected_status = DatasetStatus(args.status) if args.status else None
        manifests = service.list_datasets(status=selected_status, tag=args.tag)
        print(json.dumps([item.model_dump(mode="json") for item in manifests], indent=2))

    elif args.command == "show":
        result = service.get_dataset(args.dataset_id, args.version)
        print(result.model_dump_json(indent=2))

    elif args.command == "add-entry":
        entry = DatasetEntry(
            name=args.name,
            input=args.input,
            expected_output=args.expected_output,
            category=args.category,
            tags=args.tag,
        )
        dataset = service.add_entry(args.dataset_id, entry, created_by="cli")
        print(f"Created version {dataset.manifest.latest_version}")

    elif args.command == "set-status":
        dataset = service.set_status(args.dataset_id, DatasetStatus(args.status))
        print(dataset.manifest.status.value)

    elif args.command == "rollback":
        dataset = service.rollback(args.dataset_id, args.version, created_by="cli")
        print(f"Created version {dataset.manifest.latest_version}")

    elif args.command == "export":
        payload = service.export_version(args.dataset_id, args.version)
        rendered = json.dumps(payload, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)

    elif args.command == "import":
        payload = json.loads(args.input_file.read_text(encoding="utf-8"))
        raw_entries = payload["entries"] if isinstance(payload, dict) else payload
        dataset = service.import_entries(
            args.dataset_id,
            raw_entries,
            replace=args.replace,
            created_by="cli",
        )
        print(f"Created version {dataset.manifest.latest_version}")


if __name__ == "__main__":
    main()
