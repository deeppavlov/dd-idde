#!/usr/bin/env python3.9
import sys, pathlib

deps_path = pathlib.Path(__file__).parent.absolute() / "deps.zip"
sys.path.insert(0, str(deps_path))

import json
import libcst as cst
import libcst.matchers as m
from libcst.metadata import PositionProvider

from parse import find_flow


data = json.loads(sys.stdin.read())
python_code: str = data["pyData"]
line: int = data["line"]

wrapper = cst.MetadataWrapper(cst.parse_module(python_code))
module = wrapper.module
pos_data = wrapper.resolve(PositionProvider)
plot = find_flow(module)
assert plot

nodes = [
    (flow, el)
    for flow in plot.elements
    for el in flow.value.elements
    if not m.matches(flow, m.DictElement(key=m.Name("GLOBAL")))
]

for flow, node in nodes:
    pos = pos_data[node]
    if pos.start.line <= line <= pos.end.line:
        break
else:
    flow, node = min(nodes, key=lambda n: abs(pos_data[n[1]].start.line - line))

ret = {
    "nodeName": module.code_for_node(node.key),
    "flowName": module.code_for_node(flow.key),
}
sys.stdout.write(json.dumps(ret))
