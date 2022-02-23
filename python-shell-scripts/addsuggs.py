#!/usr/bin/env python3.9
import sys, pathlib
from pprint import pprint

deps_path = pathlib.Path(__file__).parent.absolute() / "deps.zip"
sys.path.insert(0, str(deps_path))

import json, base64
import libcst as cst
from typing import cast
from libcst.metadata import PositionProvider, CodeRange

from parse import ListUpdate, ValueUpdate, find_flow, NodeVisitor, DictUpdate


def unesc(s: str):
    return (
        s.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#10;", "\n")
    )


class CustomCondFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)
    cond_pos = None

    def __init__(self, target_cnd: str, module: cst.Module):
        self.target_cnd = target_cnd
        self.tree = module

    def visit_Lambda(self, node: cst.Lambda) -> None:
        sys.stderr.write("lambda:\n")
        pprint(node, stream=sys.stderr)
        sys.stderr.write(f"lambda code:\n{self.tree.code_for_node(node)}\n")
        sys.stderr.write("\n")
        if self.target_cnd == self.tree.code_for_node(node):
            pos = cast(CodeRange, self.get_metadata(PositionProvider, node)).start
            end = cast(CodeRange, self.get_metadata(PositionProvider, node)).end
            self.cond_pos = {"line": pos.line, "col": pos.column, "end": end.column}


data = json.loads(sys.stdin.read())
python_code: str = data["pyData"]
node_title = unesc(data["title"])
sfc = unesc(data.get("sfc", ""))
midas = unesc(data.get("midas", ""))
flow = unesc(data["flow"])
parent = unesc(data["parent"])
cnd = unesc(data["cnd"])

update_dict = {
    flow: {
        parent: {"TRANSITIONS": {node_title: cnd}},
        node_title: {
            "RESPONSE": "''",
            "TRANSITIONS": {},
        },
    }
}
if sfc != "" or midas != "":
    update_dict[flow][node_title]["MISC"] = {}
if sfc != "":
    update_dict[flow][node_title]["MISC"]['"speech_functions"'] = ListUpdate(
        [ValueUpdate(sfc)], allow_extra=False
    )
if midas != "":
    update_dict[flow][node_title]["MISC"]['"dialog_act"'] = midas
update = DictUpdate.from_dict(update_dict)

module = cst.parse_module(python_code)
old_flow = find_flow(module)
ret = {}
if old_flow:
    sys.stderr.write("visit:\n")
    new_flow = cast(cst.Dict, old_flow.visit(NodeVisitor(update, module)))
    sys.stderr.write("\n")
    new_ast = cast(cst.Module, module.deep_replace(old_flow, new_flow))
    if cnd == "lambda ctx, actor, *args, **kwargs: True":
        wrapper = cst.MetadataWrapper(new_ast)
        finder = CustomCondFinder(cnd, new_ast)
        wrapper.visit(finder)
        assert finder.cond_pos is not None
        ret["customCondPos"] = finder.cond_pos
    python_code = new_ast.code
    if module.has_trailing_newline:
        if not python_code.endswith(module.default_newline):
            python_code += module.default_newline
    else:
        python_code = python_code.rstrip(module.default_newline)

base64response = base64.b64encode(bytes(python_code, "utf-8")).decode("utf-8")
ret["pycode"] = base64response
sys.stdout.write(json.dumps(ret))
