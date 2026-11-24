"""Generate an exact uninstall allowlist and build-only license inventory."""
from importlib.metadata import distributions
from pathlib import Path
import argparse
import hashlib
import json


def prepare(bundle, output):
    bundle = Path(bundle).resolve(strict=True)
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    if not (bundle/"GooseCAD.exe").is_file():
        raise ValueError("Missing frozen executable")
    rows = []
    dirs = []
    for path in sorted(bundle.rglob("*")):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise ValueError("Nonregular bundle member")
        rel = str(path.relative_to(bundle))
        if any(c in rel for c in ('$', '"', '\n', '\r')):
            raise ValueError("Unsupported installer path")
        if path.is_dir():
            dirs.append(rel)
        else:
            with path.open("rb") as source:
                digest = hashlib.file_digest(source,"sha256").hexdigest()
            rows.append({"path":rel,"bytes":path.stat().st_size,"sha256":digest})
    if any(Path(r["path"]).name.lower() in ("opengl32.dll","osmesa.dll","libgallium_wgl.dll")
           for r in rows):
        raise ValueError("Do not package CI software OpenGL drivers")
    # Only remove files from the build manifest. Never recursively remove
    # user data or application settings during uninstall.
    lines = [f'Delete "$INSTDIR\\{r["path"]}"' for r in rows]
    lines += [f'RMDir "$INSTDIR\\{d}"' for d in sorted(dirs,key=lambda d:(len(Path(d).parts),d),reverse=True)]
    (output/"uninstall-files.nsh").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (output/"bundle-inventory.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    metadata = []
    for dist in distributions():
        metadata.append({
            "name":dist.metadata.get("Name"),"version":dist.version,
            "license_expression":dist.metadata.get("License-Expression"),
            "license_classifiers":[x for x in dist.metadata.get_all("Classifier",[]) if x.startswith("License ::")],
            "license_files":[str(x) for x in (dist.files or []) if any(s in x.name.lower() for s in ("license","licence","notice","copying"))],
        })
    metadata.sort(key=lambda x:(x["name"] or "").lower())
    (output/"dependency-inventory.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(f"Bundle files: {len(rows)}; bytes: {sum(r['bytes'] for r in rows)}; license metadata is not a distribution clearance.")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("bundle")
    parser.add_argument("output")
    args=parser.parse_args()
    prepare(args.bundle,args.output)
