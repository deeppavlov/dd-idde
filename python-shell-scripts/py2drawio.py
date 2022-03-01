#!/usr/bin/env python3.9
import sys, pathlib
deps_path = pathlib.Path(__file__).parent.absolute() / "deps.zip"
sys.path.insert(0, str(deps_path))

import json
from base64 import b64encode
import libcst as cst
from libcst.metadata import PositionProvider
from parse import find_flow
from typing import Dict, List, Any, Optional, Tuple, cast

def esc(s: str):
    return s.replace("&", "&amp;") \
        .replace("<", "&lt;") \
        .replace(">", "&gt;") \
        .replace("\"", "&quot;") \
        .replace("\n", "&#10;")

class Node:
    """
    Representation of global or local nodes.
    """
    name: str
    misc: Dict[str, str]
    transitions: Dict[Tuple[str, str], str]
    sfcs: List[str]
    midas: Optional[str] = None

    def __init__(self, name: str, flow_name: str, node: cst.Dict, module: cst.Module):
        self.name = name
        self.flow_name = flow_name
        self.misc = {}
        self.transitions = {}
        self.sfcs = []
        for node_prop_el in node.elements:
            if not isinstance(node_prop_el, cst.DictElement): continue
            prop_name = module.code_for_node(node_prop_el.key)
            if prop_name == 'TRANSITIONS':
                # sys.stderr.write(f"{name} transitions:\n{node_prop_el.value}\n")
                if isinstance(node_prop_el.value, cst.Dict):
                    self._parse_transitions(node_prop_el.value, module)
            elif prop_name == 'MISC':
                if isinstance(node_prop_el.value, cst.Dict):
                    self._parse_misc(node_prop_el.value, module)

    def _parse_transitions(self, trans: cst.Dict, module: cst.Module):
        for elem in trans.elements:
            if not isinstance(elem, cst.DictElement): continue
            if isinstance(elem.key, cst.Tuple):
                flow = module.code_for_node(elem.key.elements[0].value)
                target_name = module.code_for_node(elem.key.elements[1].value)
            else:
                flow = self.flow_name
                target_name = module.code_for_node(elem.key)
            desc = module.code_for_node(elem.value)
            self.transitions[(flow, target_name)] = desc

    def _parse_misc(self, misc: cst.Dict, module: cst.Module):
        for elem in misc.elements:
            if not isinstance(elem, cst.DictElement): continue
            if 'speech_functions' in getattr(elem.key, "value", "") and isinstance(elem.value, cst.List):
                self.sfcs = [ module.code_for_node(e.value) for e in elem.value.elements ]
            if 'dialog_act' in getattr(elem.key, "value", "") and isinstance(elem.value, cst.SimpleString):
                self.midas = module.code_for_node(elem.value)


def parse_flow(flow_node: cst.Dict, module: cst.Module, wrapper: cst.MetadataWrapper):
    """
    Parse a flow from a cst.Dict
    """
    pos_data = wrapper.resolve(PositionProvider)
    nodes = {}
    node_id = 4
    valid_node_names = set()
    for flow_el in flow_node.elements:
        if not isinstance(flow_el, cst.DictElement): continue
        flow_name = module.code_for_node(flow_el.key)
        if flow_name == "GLOBAL": continue
        flow = {}
        for node_el in cast(cst.Dict, flow_el.value).elements:
            if not isinstance(node_el, cst.DictElement): continue
            node_name = module.code_for_node(node_el.key)
            if node_name == "LOCAL": continue
            if isinstance(node_el.key, cst.SimpleString):
                valid_node_names.add(node_el.key.raw_value)
            else:
                valid_node_names.add(node_name)

            node = Node(node_name, flow_name, cast(cst.Dict, node_el.value), module)
            pos = pos_data[node_el].start
            node_data: Dict[str, Any] = {
                "id": node_id,
                "sfcs": node.sfcs,
                "midas": node.midas,
                "edges": {},
                "pos": {
                    "line": pos.line,
                    "col": pos.column
                }
            }
            node_id += 3 # Each node will need to ids

            for target, desc in node.transitions.items():
                # sys.stderr.write(f"Edge from node {node_name} -> {target}\n")
                node_data['edges'][target] = {
                    "title": desc,
                    "id":  node_id
                }
                node_id += 3 # Each edge will need three cells
            flow[node_name] = node_data
        nodes[flow_name] = flow
    return nodes, valid_node_names


def graph2drawio(graph, valid_node_names):
    """
    Convert graph to .drawio data
    """
    edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;noEdgeStyle=1;orthogonal=1;"
    diagram_id = b64encode("flow".encode()).decode()
    head = f"""<mxfile host="65bd71144e" scale="1" border="0">
        <diagram id="{diagram_id}" name="Page-1">
            <mxGraphModel dx="1494" dy="610" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
                <root>
                    <mxCell id="0"/>
                    <mxCell id="2" flows_name= "flow" value="flow" parent="0" nodenames="{esc(json.dumps(list(valid_node_names)))}"/>
    """
    tail = """
                    <mxCell id="3" value="Suggestions" parent="0"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>"""

    output = head
    y_shift = 0
    for flow_name, flow_data in graph.items():
        flow_name = esc(flow_name)
        for node_name, data in flow_data.items():
            if len(data['sfcs']) > 0:
                sfcs = data['sfcs'][0]
            else:
                sfcs = ""
            midas = data['midas'] if data['midas'] else ""
            sys.stderr.write(f"{sfcs}\n")
            # assert False
            data_from_form = {
                "node_title": node_name,
                "old_titles": [node_name],
                "sfc": sfcs,
                "midas": midas
            }
            data_from_form = esc(json.dumps(data_from_form))
            # sys.stderr.write(f"{node_name}: {data['id']}\n")
            node_name = esc(node_name)
            pos = esc(json.dumps(data['pos']))
            node_text = f"""
                <UserObject data_from_form="{data_from_form}" label="{node_name}" id="{data['id']}" pos="{pos}">
                    <mxCell id="{data['id'] + 1}" label="{node_name}" style="swimlane;fontStyle=0;fontColor=default;childLayout=stackLayout;horizontal=1;startSize=26;fillColor=#dae8fc;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;strokeColor=#6c8ebf;autosize=1;" vertex="1" parent="2" collapsed="1">
                          <mxGeometry x="150" y="{70 + y_shift}" width="150" height="26" as="geometry">
                              <mxRectangle x="10" y="40" width="150" height="90" as="alternateBounds" />
                          </mxGeometry>
                    </mxCell>
                </UserObject>
                <mxCell isnode="1" pos="{pos}" id="{data['id'] + 2}" old_title="{node_name}" parent="{data['id']}" label="{node_name}" value="" flow="{flow_name}" style="text;strokeColor=none;fontColor=default;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontStyle=2;whiteSpace=wrap" vertex="1" >
                    <mxGeometry y="26" width="150" height="64" as="geometry" />
                </mxCell>
            """
            output += node_text
            for (target_flow, target_name), edge_data in data['edges'].items():
                # sys.stderr.write(f"{edge_data}\n")
                try:
                    target_id = graph[target_flow][target_name]['id']
                except KeyError:
                    continue
                if isinstance(target_id, str):
                    target_id = esc(target_id)
                parsed = cst.parse_expression(edge_data['title'])
                cndlist = []
                if isinstance(parsed, cst.Call) and len(parsed.args) > 0:
                    mod = cst.parse_module(edge_data['title'])
                    if isinstance(parsed.args[0].value, cst.List):
                        cndlist = [mod.code_for_node(el.value) for el in parsed.args[0].value.elements]
                        if isinstance(parsed.func, cst.Attribute):
                            title = parsed.func.attr.value.capitalize()
                        else:
                            title = edge_data['title']
                    elif "sf" in mod.code_for_node(parsed.func):
                        title = mod.code_for_node(parsed.args[0])
                    else:
                        title = edge_data['title']
                else:
                    title = edge_data['title']
                title = esc(title)
                edge_text = f"""
                    <mxCell isedge="1" id="{edge_data['id']}" flow="{flow_name}" style="{edge_style}" parent="2" source="{data["id"]}" target="{edge_data['id'] + 1}" reallabel="{esc(edge_data['title'])}" realtarget="{int(target_id)}" edge="1">
                        <mxGeometry relative="1" as="geometry">
                            <Array as="points">
                                <mxPoint x="150" y="{70 + y_shift}"/>
                                <mxPoint x="150" y="{70 + y_shift}"/>
                            </Array>
                        </mxGeometry>
                    </mxCell>
                    <mxCell id="{edge_data['id'] + 2}" flow="{flow_name}" style="{edge_style}" parent="2" source="{edge_data['id'] + 1}" target="{target_id}" edge="1">
                        <mxGeometry relative="1" as="geometry">
                            <Array as="points">
                                <mxPoint x="150" y="{70 + y_shift}"/>
                                <mxPoint x="150" y="{70 + y_shift}"/>
                            </Array>
                        </mxGeometry>
                    </mxCell>
                    <mxCell id="{edge_data['id'] + 1}" value="{title}" style="swimlane;fontColor=default;fontStyle=0;childLayout=stackLayout;horizontal=1;startSize=26;fillColor=#fff2cc;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;strokeColor=#d6b656;autosize=1;" vertex="1" parent="2" collapsed="1">
                          <mxGeometry x="150" y="{70 + y_shift}" width="150" height="26" as="geometry">
                              <mxRectangle x="10" y="40" width="150" height="90" as="alternateBounds" />
                          </mxGeometry>
                    </mxCell>
                """
                for cnd in cndlist:
                    edge_text += f"""
                        <mxCell parent="{edge_data['id'] + 1}" value="{esc(cnd)}" style="text;strokeColor=none;fontColor=default;fillColor=white;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontStyle=2;whiteSpace=wrap" vertex="1" >
                            <mxGeometry y="26" width="150" height="30" as="geometry" />
                        </mxCell>
                    """
                output += edge_text
        y_shift += 300
    output += tail
    return output


def pipeline(content):
    module = cst.parse_module(content)
    wrapper = cst.MetadataWrapper(module)
    module = wrapper.module
    flow_node = find_flow(module)
    assert flow_node is not None
    nodes, valid_node_names = parse_flow(flow_node, module, wrapper)
    xml = graph2drawio(nodes, valid_node_names)
    return xml


content = sys.stdin.read()
data = pipeline(content)
sys.stdout.write(data)
