#!/usr/bin/env python3.9
import base64
import json
import ast
import sys
import libcst as cst
import libcst.matchers as m
from lxml import etree
from dataclasses import dataclass
from collections import defaultdict
from typing import Optional, List, Dict


class Transition:
    def __init__(self, func):
        self.func = func
        if self.func != "":
            try:
                self.parsed = ast.parse(func).body[0].value
            except IndexError:  # No data to parse. Return empty string
                self.parsed = '""'
            if isinstance(self.parsed, (ast.Constant, ast.Call)):
                pass
            elif isinstance(self.parsed, ast.Attribute):
                self.func = f'cnd.all([dm_cnd.is_sf("{self.func}")])'
        else:
            self.func = '""'

    def __repr__(self):
        return str(self.func)


class Processing:
    def __init__(self, func):
        self.func = func

    def __repr__(self):
        return str(self.func)


@dataclass
class UpdatedNode:
    transitions: Dict[str, Transition]
    speech_func: str = ""


class NodeVisitor(m.MatcherDecoratableTransformer):
    need_misc: bool = False
    updated_nodes: Dict[str, Dict[str, UpdatedNode]]
    dict_stack: List[cst.Dict] = []
    key_stack: List[str] = []
    target_elements: Optional[Dict[str, str]] = None
    current_node: Optional[UpdatedNode] = None
    example_dict: Dict[int, cst.Dict] = {}
    example_comma: Dict[int, cst.Comma] = {}
        
    def _formatted_dict(self, offset = 0):
        level = len(self.dict_stack) + offset
        return cst.parse_expression(f"{{\n{'    ' * level}\n}}")
    
    def _formatted_comma(self):
        level = len(self.dict_stack)
        return cst.Comma(
            whitespace_before=cst.SimpleWhitespace(''),
            whitespace_after=cst.ParenthesizedWhitespace(
                first_line=cst.TrailingWhitespace(
                    whitespace=cst.SimpleWhitespace(''),
                    comment=None,
                    newline=cst.Newline(value=None),
                ),
                empty_lines=[],
                indent=True,
                last_line=cst.SimpleWhitespace(
                    value='    ' * level,
                )
            )
        )
    
    def __init__(self, updated_nodes: Dict[str, Dict[str, UpdatedNode]]):
        super().__init__()
        self.updated_nodes = updated_nodes

    @m.call_if_inside(
        m.SimpleStatementLine(body=[m.Assign(value=m.Dict())])
    )
    def visit_Dict(self, node: cst.Dict) -> None:
        self.dict_stack.append(node)
        if len(node.elements) > 0:
            self.example_dict[len(self.dict_stack)] = node
        keys = [el.key.value for el in node.elements if hasattr(el.key, "value")]
        if len(self.dict_stack) == 3 and 'TRANSITIONS' in keys:
            self.current_node = self.updated_nodes.get(self.key_stack[0], {}).get(self.key_stack[1], None)
            if self.current_node:
                self.need_misc = self.current_node.speech_func != ""
        elif self.current_node is not None:
            if self.key_stack[-1] == 'TRANSITIONS':
                self.target_elements = self.current_node.transitions.copy()
            elif self.key_stack[-1] == 'MISC':
                self.target_elements = { "speech_functions": [self.current_node.speech_func] }
                self.need_misc = False
    
    @m.call_if_inside(
        m.SimpleStatementLine(body=[m.Assign(value=m.Dict())])
    )
    def leave_Dict(self, node: cst.Dict, upd_node: cst.Dict) -> None:
        if self.target_elements is not None:
            new_els = [cst.DictElement(
                key=cst.SimpleString(f"'{k}'"),
                value=cst.parse_expression(repr(v))) for k, v in self.target_elements.items()]
            if len(upd_node.elements) == 0:
                upd_node = self.example_dict.get(len(self.dict_stack), self._formatted_dict()).with_changes(
                    elements=[]
                )
                prev = upd_node.elements
            else:
                last = upd_node.elements[-1].with_deep_changes(
                    upd_node.elements[-1],
                    comma=self.example_comma.get(len(self.dict_stack), self._formatted_comma())
                )
                prev = [*upd_node.elements[:-1], last]
            upd_node = upd_node.with_changes(
                elements=[*prev, *new_els]
            )
        self.target_elements = None
        if len(self.dict_stack) < 4:
            if self.need_misc:
                prev = upd_node.elements[-1].with_deep_changes(
                    upd_node.elements[-1],
                    comma=self.example_comma.get(len(self.dict_stack), self._formatted_comma())
                )
                new_dict = self.example_dict.get(len(self.dict_stack)+1, self._formatted_dict(1)).with_changes(
                    elements=[cst.DictElement(
                        key=cst.SimpleString('"speech_functions"'),
                        value=cst.parse_expression(repr([self.current_node.speech_func]))
                    )]
                )
                new_el = upd_node.elements[-1].with_deep_changes(
                    upd_node.elements[-1],
                    key=cst.Name('MISC'),
                    value=new_dict
                )
                upd_node = upd_node.with_changes(
                    elements=[*upd_node.elements[:-1], prev, new_el]
                )
            self.current_node = None
        self.dict_stack.pop()
        return upd_node
        
    
    @m.call_if_inside(
        m.DictElement(value=m.Dict())
    )
    def visit_DictElement(self, node: cst.DictElement):
        if m.matches(node.comma, m.ParenthesizedWhitespace()):
            self.example_comma[len(self.dict_stack)] = node.comma
        if hasattr(node.key, "raw_value"):
            self.key_stack.append(node.key.raw_value)
        elif hasattr(node.key, "value"):
            self.key_stack.append(node.key.value)
        else:
            self.key_stack.append("")
            return False
    
    @m.call_if_inside(
        m.DictElement(value=m.Dict())
    )
    def leave_DictElement(self, node: cst.DictElement, upd_node: cst.DictElement):
        key = self.key_stack.pop()
        
        if self.target_elements is not None:
            if key in self.target_elements:
                val = self.target_elements[key]
                del self.target_elements[key]
                if isinstance(upd_node.value, cst.SimpleString):
                    snode = upd_node.value
                    val = upd_node.value.with_changes(
                        value=snode.prefix + snode.quote + str(val) + snode.quote
                    )
                elif isinstance(upd_node.value, cst.Name):
                    val = upd_node.value.with_changes(
                        value=str(val)
                    )
                elif isinstance(upd_node.value, cst.List):
                    val = cst.parse_expression(repr(val))
                    for el in upd_node.value.elements:
                        if el.deep_equals(val):
                            val = upd_node.value
                            break
                #     else:
                #         val = upd_node.value.with_changes(
                #             elements=[*upd_node.value.elements, val]
                #         )
                else:
                    val = cst.parse_expression(repr(val))
                return upd_node.with_deep_changes(
                    upd_node,
                    value=val
                )
            elif self.key_stack[-1] == "TRANSITIONS":
                return cst.RemoveFromParent()
        return upd_node
            

def parse_file(drawio_fn):
    elems = etree.fromstring(drawio_fn).xpath('//root')[0].getchildren()
    nodes = {}
    edges = {}

    for node in elems:
        try:
            mxChild = node.getchildren()[0]
            mxStyle = mxChild.attrib['style']
        except Exception as e:
            mxStyle = ""
        if node.attrib['id'] == "2":
            flows_name = node.attrib['flows_name']
        if "rounded=0;whiteSpace=wrap;html=1;" in mxStyle:  # Node
            if "edgeLabel" in mxChild.attrib['style']:
                continue
            nodes[int(node.attrib['id'])] = {
                'title': node.attrib['label'], 'node': node}
        elif node.tag == 'mxCell' or node.tag == 'object' or "edgeStyle" in mxStyle:
            try:
                node_title = node.attrib['value']
            except KeyError:
                node_title = ""
                if node.attrib['id'] not in {'0', '1', '2'}:
                    for sibling in node.itersiblings():
                        try:
                            sibling.getchildren()[0].attrib['parent']
                        except Exception as e:
                            continue
                        if sibling.getchildren()[0].attrib['parent'] == node.attrib['id']:
                            from_form = json.loads(
                                sibling.attrib['data_from_form'])
                            node_title = from_form['sfc']
            if node.tag == 'object':
                node = mxChild
            elif "edgeStyle" in mxStyle:
                from_form = json.loads(node.attrib['data_from_form'])
                node_title = from_form['sfc']
                node = mxChild
            try:
                node.attrib['style']
            except KeyError:  # Not an arrow
                continue
            try:
                edges[int(node.attrib['source'])]
            except KeyError:
                edges[int(node.attrib['source'])] = {}
            try:  # Try to get text value of edge between nodes
                edges[int(node.attrib['source'])][int(
                    node.attrib['target'])] = node_title
            except KeyError:
                edges[int(node.attrib['source'])][int(
                    node.attrib['target'])] = ""
    return nodes, edges, flows_name


def get_updated_nodes(nodes, edges):
    updated = defaultdict(dict)
    for node_dict in nodes.values():
        node = node_dict['node']
        flow_name = node.attrib['flow']
        from_form = json.loads(node.attrib['data_from_form'])

        # Check if node name contains Speech Function
        node_name = node.attrib['label'].split(" ")
        if len(node_name) > 1:
            node_name, sfc = node_name[:2]
        else:
            node_name = node_name[0]
            sfc = from_form['sfc']
        # Transitions
        # Check if node has child nodes
        transitions = {}
        try:
            for edge, edge_title in edges[int(node.attrib['id'])].items():
                target_data = json.loads(
                    nodes[edge]['node'].attrib['data_from_form'])
                # Compare flow of source node and flow of target node.
                # If !=, then add tuple to transition
                if node.attrib['flow'] != nodes[edge]['node'].attrib['flow']:
                    # Tuple: ( <flow of target node>, <name of target node> )
                    target_title = (
                        nodes[edge]['node'].attrib['flow'],
                        target_data['node_title']
                    )
                else:
                    target_title = target_data['node_title']
                transitions[target_title] = Transition(edge_title)
        except KeyError:
            pass
        
        updated[flow_name][node_name] = UpdatedNode(
            transitions=transitions,
            speech_func=sfc
        )
    return updated

def fix_missing_flows(nodes, edges):
    for node_dict in nodes.values():
        node = node_dict['node']
        try:
            node.attrib['flow']
        except KeyError:
            for source, target in edges.items():
                try:  # If we find missing flow, check flow of parent node
                    target[int(node.attrib['id'])]
                    node.attrib['flow'] = nodes[source]['node'].attrib['flow']
                except KeyError:
                    continue
    return nodes, edges


def find_flow(content, tree):
    """
    Find node that contains flow data to replace it with new code
    """
    keywords = [
        "GLOBAL",
        "LOCAL",
        "TRANSITIONS",
        "PROCESSING"
        "RESPONSE",
        "GLOBAL_TRANSITIONS"
    ]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.Dict):
                    inner_data = ast.get_source_segment(content, child)
                    for kword in keywords:
                        if kword in inner_data:
                            return ast.get_source_segment(content, node)
    return None


def pipeline(content):
    nodes, edges, flows_name = parse_file(content)
    nodes, edges = fix_missing_flows(nodes, edges)
    updated = get_updated_nodes(nodes, edges)
    return updated


# Receiving data from Extension (JSON: { 'xmlData': ..., 'pyData': .... })
extensionData = sys.stdin.read()
extensionDataDict = json.loads(extensionData)
pythonCode = extensionDataDict['pyData']
# Parse old Python code to find node with Flow data
pyAstTree = ast.parse(pythonCode)
flowToReplace = find_flow(pythonCode, pyAstTree)
# Convert Drawio content to Python dict
updated = pipeline(extensionDataDict['xmlData'])
tree = cst.parse_module(pythonCode)
new_tree = tree.visit(NodeVisitor(updated))
# sys.stderr.write(repr(new_tree))
pythonCode = new_tree.code

base64response = base64.b64encode(bytes(pythonCode, 'utf-8')).decode('utf-8')
response = json.dumps({'pyCode': base64response})
sys.stdout.write(response)
# print(str(pythonCode))
