#!/usr/bin/env python3.9
import sys, pathlib
deps_path = pathlib.Path(__file__).parent.absolute() / "deps.zip"
sys.path.insert(0, str(deps_path))

import base64
import json
import libcst as cst
from lxml import etree
from collections import defaultdict
from typing import Dict, Union, cast

from parse import KeyUpdate, ListUpdate, ValueUpdate, find_flow, NodeVisitor, DictUpdate

def unesc(s: str):
    return s.replace("&amp;", "&") \
        .replace("&lt;", "<") \
        .replace("&gt;", ">") \
        .replace("&quot;", "\"") \
        .replace("&#10;", "\n")

def parse_file(drawio_fn):
    sys.stderr.write(f"{drawio_fn}\n\n")
    doc = etree.fromstring(drawio_fn)
    elems = doc.xpath("//root")[0].getchildren()
    nodes = {}
    edge_flows = {}
    edges = defaultdict(dict)

    for node in elems:
        if 'isnode' in node.attrib:
            usr_obj = doc.xpath(f"//*[@id='{node.attrib['parent']}']")
            if len(usr_obj) > 0 and 'data_from_form' in usr_obj[0].attrib:
                form_data = json.loads(unesc(usr_obj[0].attrib['data_from_form']))
            else:
                form_data = {}
            title = form_data.get('node_title', node.attrib['label'])
            old_titles = form_data.get('old_titles', [unesc(node.attrib['old_title']), None])
            if len(old_titles) > 1:
                old_title = old_titles[-2]
            else:
                old_title = old_titles[0]
            if 'node_title' not in form_data:
                form_data['node_title'] = title
            nodeid = int(node.attrib['parent'])
            sys.stderr.write(f'NODE: {old_title}: #{nodeid}\n')
            nodes[nodeid] = {
                "old_title": old_title,
                "title": title,
                "node": node,
                "form_data": form_data
            }
        elif 'isedge' in node.attrib:
            try:
                sys.stderr.write(f"target: " + str(doc.xpath(f"//*[@source='{int(node.attrib['target'])}']")[0].attrib) + '\n')
                realtarget = doc.xpath(f"//*[@source='{int(node.attrib['target'])}']")[0].attrib['target']
                sys.stderr.write(f'EDGE: {node} {int(node.attrib["source"])} -> {int(realtarget)} : {unesc(node.attrib["reallabel"])}\n')
                edges[int(node.attrib["source"])][ int(realtarget) ] = unesc(node.attrib['reallabel'])
            except Exception:
                pass
    return nodes, edges, edge_flows


def get_updated_nodes(nodes, edges):
    sys.stderr.write(f"nodes: {nodes}")
    updated = defaultdict(dict)
    renames = {}
    valid_node_names = defaultdict(set)
    for node_dict in nodes.values():
        node = node_dict["node"]
        flow_name = unesc(node.attrib["flow"])
        from_form = node_dict['form_data']

        old_title = node_dict['old_title']
        node_name = node_dict['title']
        if old_title != node_name:
            renames[old_title] = node_name
        sfc = from_form.get("sfc", "")
        midas = from_form.get("midas", "")

        node_key = KeyUpdate(old_key=old_title, new_key=node_name)
        updated[flow_name][node_key] = {
            "TRANSITIONS": {},
        }
        valid_node_names[flow_name].add(node_name)

        if sfc != "" or midas != "":
           updated[flow_name][node_key]["MISC"] = {}
        if sfc != "":
            updated[flow_name][node_key]["MISC"]['"speech_functions"'] = ListUpdate([sfc], order_significant=True, reverse=True)
        if midas != "":
            updated[flow_name][node_key]["MISC"]['"dialog_act"'] = midas
            

    for node_dict in nodes.values():
        node = node_dict["node"]
        flow_name = unesc(node.attrib["flow"])
        old_title = node_dict['old_title']
        node_name = node_dict['title']
        transitions: Dict[Union[str, KeyUpdate], Union[str, ValueUpdate]] = {}
        sys.stderr.write(f"EDGES for {old_title}:\n{edges[int(node.attrib['parent'])]}\n")
        for edge, edge_title in edges[int(node.attrib["parent"])].items():
            sys.stderr.write(f"node#{edge} found: {edge in nodes}\n")
            if edge not in nodes: continue
            target_data = nodes[edge]["form_data"]
            sys.stderr.write(f"node: {node_name}, flow name {node.attrib['flow']}, target flow {nodes[edge]['node'].attrib['flow']}\n")
            if unesc(node.attrib["flow"]) != unesc(nodes[edge]["node"].attrib["flow"]):
                target_flow = unesc(nodes[edge]['node'].attrib['flow'])
                new_target_node = target_data['node_title']
                old_target_node = next((o for o, n in renames.items() if n == new_target_node), new_target_node)
                sys.stderr.write(f"flow name {target_flow}, node name (new) {new_target_node}, (old) {old_target_node}\n")
                old_name = f"({target_flow}, {old_target_node})"
                new_name = f"({target_flow}, {new_target_node})"
                val = edge_title
                transitions[KeyUpdate(old_key=old_name, new_key=new_name)] = val
                if old_target_node != new_target_node:
                    sys.stderr.write(f"trans {old_title} -> {old_name}={new_name}\n")
            else:
                new_name = target_data["node_title"] 
                old_name = next((o for o, n in renames.items() if n == new_name), new_name) 
                val = edge_title
                transitions[KeyUpdate(old_key=old_name, new_key=new_name)] = val
                if new_name != old_name:
                    sys.stderr.write(f"trans {old_title} -> {old_name}={new_name}\n")
        sys.stderr.write(f"TRANSITIONS for {old_title}:\n{transitions}\n\n")
        transitions_upd = DictUpdate.from_dict(transitions)
        transitions_upd.allow_extra = False
        updated[flow_name][old_title]['TRANSITIONS'] = transitions_upd


    updated = { fn: DictUpdate(fc, allow_extra=False) for fn, fc in updated.items() }
        
    upd = DictUpdate.from_dict(updated)
    upd.allow_extra = False
    return upd, valid_node_names


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

updated, valid_node_names = parse_xml(data["xmlData"])
module = cst.parse_module(python_code)
old_flow = find_flow(module)
if old_flow:
    new_flow = cast(cst.Dict, old_flow.visit(NodeVisitor(updated, module)))
    # assert False
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

