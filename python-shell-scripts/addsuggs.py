#!/usr/bin/env python3.9
import sys, pathlib
deps_path = pathlib.Path(__file__).parent.absolute() / "deps.zip"
sys.path.insert(0, str(deps_path))

import json, base64
import libcst as cst
from typing import cast

from parse import ListUpdate, ValueUpdate, find_flow, NodeVisitor, DictUpdate


data = json.loads(sys.stdin.read())
python_code: str = data["pyData"]
node_title = f'"{data["title"]}"'
sfc = f'"{data.get("sfc", "")}"'
flow = f'"{data["flow"]}"'
parent = f'"{data["parent"]}"'
cnd = data["cnd"]

update_dict = {
    flow: {
        parent: {
            "TRANSITIONS": {
                node_title: cnd
            }
        },
        node_title: {
            "TRANSITIONS": {},
            "RESPONSE": "''",
        }
    }
}
if sfc != '""':
    update_dict[node_title]["MISC"] = {}
    update_dict[node_title]["MISC"]['"speech_functions"'] = ListUpdate([ValueUpdate(sfc)], allow_extra=False)
update = DictUpdate.from_dict(update_dict)

module = cst.parse_module(python_code)
old_flow = find_flow(module)
if old_flow:
    new_flow = cast(cst.Dict, old_flow.visit(NodeVisitor(update, module)))
    python_code = cast(cst.Module, module.deep_replace(old_flow, new_flow)).code
    if module.has_trailing_newline:
        if not python_code.endswith(module.default_newline):
            python_code += module.default_newline
    else:
        python_code = python_code.rstrip(module.default_newline)

base64response = base64.b64encode(bytes(python_code, "utf-8")).decode("utf-8")
sys.stdout.write(base64response)
