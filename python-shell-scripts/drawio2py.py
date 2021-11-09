import base64
import json
import sys
import libcst as cst
from lxml import etree
from collections import defaultdict
from typing import Optional, List, Dict, Any, cast

from parse import ListUpdate, find_flow, NodeVisitor, DictUpdate


def parse_file(drawio_fn):
    doc = etree.fromstring(drawio_fn)
    elems = doc.xpath("//root")[0].getchildren()
    nodes = {}
    edge_flows = {}
    edges = defaultdict(dict)

    for node in elems:
        if 'isnode' in node.attrib:
            usr_obj = doc.xpath(f"//*[@id='{node.attrib['parent']}']")
            if len(usr_obj) > 0 and 'data_from_form' in usr_obj[0].attrib:
                form_data = json.loads(usr_obj[0].attrib['data_from_form'])
            else:
                form_data = {}
            title = form_data.get('node_title', node.attrib['label'])
            if 'node_title' not in form_data:
                form_data['node_title'] = title
            nodeid = int(node.attrib["id"])
            nodes[nodeid] = {
                "title": title,
                "node": node,
                "form_data": form_data
            }
        elif 'isedge' in node.attrib:
            edges[int(node.attrib["source"])][
            int(node.attrib["realtarget"])
            ] = node.attrib['reallabel']
    return nodes, edges, edge_flows


def get_updated_nodes(nodes, edges) -> DictUpdate:
    updated = defaultdict(dict)
    for node_dict in nodes.values():
        node = node_dict["node"]
        flow_name = node.attrib["flow"]
        from_form = node_dict['form_data']

        node_name = node.attrib["label"]
        sfc = from_form.get("sfc", "")
        # Transitions
        # Check if node has child nodes
        transitions: Dict[str, str] = {}
        try:
            for edge, edge_title in edges[int(node.attrib["id"])].items():
                target_data = json.loads(nodes[edge]["form_data"])
                # Compare flow of source node and flow of target node.
                # If !=, then add tuple to transition
                if node.attrib["flow"] != nodes[edge]["node"].attrib["flow"]:
                    # Tuple: ( <flow of target node>, <name of target node> )
                    target_title = f"({nodes['edge']['node'].attrib['flow']}, {target_data['node_title']})"
                else:
                    target_title = target_data["node_title"]
                transitions[target_title] = edge_title
        except KeyError:
            pass

        updated[flow_name][node_name] = {
            "TRANSITIONS": transitions,
        }

        if sfc != "":
            updated[flow_name][node_name]["MISC"] = {
                '"speech_functions"': ListUpdate(['"' + sfc + '"'], allow_extra=False)
            }

    return DictUpdate.from_dict(updated)


def fix_missing_flows(nodes, edges, edge_flows):
    for node_dict in nodes.values():
        node = node_dict["node"]
        try:
            node.attrib["flow"]
        except KeyError:
            i = int(node.attrib["id"])
            for source, target in edges.items():
                if i in edge_flows:
                    node.attrib["flow"] = edge_flows[i]
                try:  # If we find missing flow, check flow of parent node
                    target[int(node.attrib["id"])]
                    node.attrib["flow"] = nodes[source]["node"].attrib["flow"]
                except KeyError:
                    continue
    return nodes, edges


def parse_xml(content):
    nodes, edges, edge_flows = parse_file(content)
    nodes, edges = fix_missing_flows(nodes, edges, edge_flows)
    updated = get_updated_nodes(nodes, edges)
    return updated


# Receiving data from Extension (JSON: { 'xmlData': ..., 'pyData': .... })
data = json.loads(sys.stdin.read())
python_code: str = data["pyData"]

updated = parse_xml(data["xmlData"])
module = cst.parse_module(python_code)
old_flow = find_flow(module)
if old_flow:
    new_flow = cast(cst.Dict, old_flow.visit(NodeVisitor(updated, module)))
    python_code = cast(cst.Module, module.deep_replace(old_flow, new_flow)).code
    if module.has_trailing_newline:
        if not python_code.endswith(module.default_newline):
            python_code += module.default_newline
    else:
        python_code = python_code.rstrip(module.default_newline)
    # sys.stdout.write(module.code_for_node(new_flow))

base64response = base64.b64encode(bytes(python_code, "utf-8")).decode("utf-8")
response = json.dumps({"pyCode": base64response})
sys.stdout.write(response)

