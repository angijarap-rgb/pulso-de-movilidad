import argparse
import json
import re
from pathlib import Path

from pulso.pipeline import write_json


def activate(root, run_id):
    if not re.fullmatch(r"\d{8}T\d{6}Z-[a-f0-9]{8}", run_id):
        raise ValueError("Identificador de ejecución inválido")
    folder = root / "versions" / run_id
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    for filename in ("history.csv", "challenger.joblib"):
        if not (folder / filename).is_file():
            raise FileNotFoundError(folder / filename)
    if "registry" in report:
        from pulso.registry import set_champion

        set_champion(root, report["registry"], report["decision"]["active"])
    write_json(root / f"active-{report['kind']}.json", {"run_id": run_id})


def main():
    parser = argparse.ArgumentParser(description="Reactiva una versión local")
    parser.add_argument("run_id")
    parser.add_argument("--root", type=Path, default=Path("runs"))
    args = parser.parse_args()
    activate(args.root, args.run_id)
    print(f"Versión activa: {args.run_id}. Reinicia la API para cargarla.")


if __name__ == "__main__":
    main()
