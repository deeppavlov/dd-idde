import ast
import sys
import json
from base64 import b64encode
import libcst as cst

class Node:
    """
    Representation of global or local nodes.
    """

    def __init__(self, name, tr, proc, resp, misc):
        self.name = name
        self.response = resp
        self.transitions = tr
        self.processing = proc
        self.misc = misc

    @classmethod
    def parse_node(cls, flow_name, node_name, node, imports, source):
        node_tuple = (flow_name, node_name)
        transitions = {}
        processing = {}
        response = ""
        misc = ""
        for key, value in zip(node.keys, node.values):
            if key.id == 'TRANSITIONS':
                func_args = []
                for tr_k, tr_v in zip(value.keys, value.values):
                    # Check type of target node data. If tuple, get flow and node names
                    target_title = ()
                    if isinstance(tr_k, ast.Tuple):  # Target node in another flow
                        if len(tr_k.elts) > 1:
                            target_title = (
                                tr_k.elts[0].value, tr_k.elts[1].value)
                        else:  # Len of tuple < 1. Data is not correct.
                            continue
                    elif isinstance(tr_k, ast.Constant):  # Target node in the same flow
                        target_title = (flow_name, tr_k.value)
                    # Check type of values in Transitions dict
                    if isinstance(tr_v, ast.Constant):
                        tr_description = f"&quot;{tr_v.value}&quot;"
                    elif isinstance(tr_v, ast.Call):
                        # print(ast.get_source_segment(content, tr_v))
                        # Check imports and functions
                        """try:
                            imports[tr_v.func.value.id]
                        except KeyError:
                            # print(f'Missing Function "{tr_v.func.value.id}": Show Error Message in VS Code')
                            ...
                        for arg in tr_v.args:
                            func_args.append(arg.value)
                        tr_description = f'{tr_v.func.value.id}.{tr_v.func.attr}({", ".join(func_args)})'"""
                        tr_description = ast.get_source_segment(
                            content, tr_v).replace('\"', '&quot;')
                    elif isinstance(tr_v, ast.Attribute):
                        tr_description = f"{tr_v.value.id}.{tr_v.attr}"
                    transitions[target_title] = tr_description
            elif key.id == 'PROCESSING':
                for proc_k, proc_v in zip(value.keys, value.values):
                    if isinstance(proc_k, ast.Constant):
                        processing[proc_k.value] = []
                        for function in proc_v.elts:
                            processing[proc_k.value].append(function.id)
            elif key.id == 'RESPONSE':
                if isinstance(value, ast.Dict):
                    continue
                elif isinstance(value, ast.Constant):
                    response = value.value
            elif key.id == "MISC":
                misc = []
                if not isinstance(value, ast.Dict):
                    continue
                if value.values:
                    if not isinstance(value.values[0], ast.List):
                        continue
                    arr = value.values[0]
                    for element in arr.elts:
                        if isinstance(element, ast.Constant):
                            misc.append(element.value)
                            #misc = ast.get_source_segment(content, value).replace("\"", "&quot;")

        return cls(node_tuple, transitions, processing, response, misc)


class Flows:
    """
    Representation of DFF flow.
    """

    def __init__(self, source, tree):
        self.source = source
        self.tree = tree
        self.imports = {}
        self.flows_name = ""
        self.global_flow = {}
        self.local_flows = {}
        self.keywords = [
            "GLOBAL",
            "LOCAL",
            "TRANSITIONS",
            "PROCESSING"
            "RESPONSE",
            "GLOBAL_TRANSITIONS"
        ]

        # Initialize flows
        self.flow = self.get_flow()
        self.get_imports()
        self.get_flows()

    def __str__(self):
        return ast.get_source_segment(self.source, self.flow)

    def get_flows(self):
        """
        Parse nodes within flows
        """
        for child in ast.iter_child_nodes(self.flow):
            if isinstance(child, ast.Name):
                self.flows_name = child.id
            elif isinstance(child, ast.Dict):
                for key, value in zip(child.keys, child.values):
                    # Flow parsing begins here
                    flow_name = self.get_name(key)
                    # print('FLOW Name:', flow_name)
                    if flow_name == "GLOBAL":
                        self.global_flow['GLOBAL'] = Node.parse_node(
                            flow_name, flow_name, value, self.imports, self.source)
                    else:
                        local_flow = {}
                        for node_key, node_val in zip(value.keys, value.values):
                            node_name = self.get_name(node_key)
                            local_flow[(flow_name, node_name)] = Node.parse_node(
                                flow_name, node_name, node_val, self.imports, self.source)
                        self.local_flows[flow_name] = local_flow

    def get_flow(self) -> ast.Assign:
        """
        Detect line with flow and return its AST.
        """
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.Dict):
                        inner_data = ast.get_source_segment(self.source, child)
                        for kword in self.keywords:
                            if kword in inner_data:
                                return node
        return None

    def get_imports(self):
        """
        Parse imports in python script
        """
        for node in self.tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for name in node.names:
                    if name.asname:
                        self.imports[name.asname] = name.name
                    else:
                        self.imports[name.name] = name.name

    def get_name(self, name):
        if isinstance(name, ast.Name):
            return name.id
        elif isinstance(name, ast.Constant):
            return name.value
        elif isinstance(name, str):
            return name


def flow2graph(flow):
    """
    Convert flow to a simple graph
    """
    nodes = {}
    # ID for XML file, {1, 2, 3} IDs are reserved for XML root nodes
    node_id = 4
    for local_flow in flow.local_flows.keys():
        nodes[local_flow] = {}
        for name, node in flow.local_flows[local_flow].items():
            if name == "LOCAL":
                continue
            node_data = {}
            edges = {}
            processing = {}
            for path, description in node.transitions.items():
                edges[path] = {"title": description, "id": node_id}
                node_id += 3 # Each edge will need three cells
            for id_, preproc in node.processing.items():
                processing[id_] = preproc
            node_data['processing'] = processing
            node_data['response'] = node.response
            node_data['misc'] = node.misc
            node_data['edges'] = edges
            node_data['id'] = node_id
            nodes[local_flow][name] = node_data
            node_id += 3 # Each node will need to ids
    return nodes


def graph2drawio(graph, flow):
    """
    Convert graph to .drawio data
    """
    edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;noEdgeStyle=1;orthogonal=1;"
    diagram_id = b64encode(flow.flows_name.encode()).decode()
    head = f"""<mxfile host="65bd71144e" scale="1" border="0">
        <diagram id="{diagram_id}" name="Page-1">
            <mxGraphModel dx="1494" dy="610" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
                <root>
                    <mxCell id="0"/>
                    <mxCell id="2" flows_name= "{flow.flows_name}" value="{flow.flows_name}" parent="0"/>
    """
    tail = """
                    <mxCell id="3" value="Suggestions" parent="0"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>"""

    output = head
    y_shift = 0
    for local_flow, flow_data in graph.items():
        for node, data in flow_data.items():
            if data['misc']:  # Check speech functions for node
                sfcs = data['misc'][0]
            else:
                sfcs = ""
            data_from_form = {
                "node_title": node[1],
                "sfc": sfcs
            }
            data_from_form = json.dumps(data_from_form).replace("\"", "&quot;")
            sys.stderr.write(f"{node[1]}: {data['id']}\n")
            node_text = f"""
                <UserObject data_from_form="{data_from_form}" label="{node[1]}" id="{data['id']}">
                    <mxCell id="{data['id'] + 1}" value="{node[1]}" style="swimlane;fontStyle=0;fontColor=default;childLayout=stackLayout;horizontal=1;startSize=26;fillColor=#dae8fc;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;strokeColor=#6c8ebf;" vertex="1" parent="2" collapsed="1">
                          <mxGeometry x="150" y="{70 + y_shift}" width="200" height="26" as="geometry">
                              <mxRectangle x="10" y="40" width="200" height="90" as="alternateBounds" />
                          </mxGeometry>
                    </mxCell>
                </UserObject>
                <mxCell isnode="1" parent="{data['id']}" label="{node[1]}" value="" flow="{local_flow}" response="{data['response']}" processing="{str(data['processing'])}" style="text;strokeColor=none;fontColor=default;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontStyle=2;whiteSpace=wrap" vertex="1" >
                    <mxGeometry y="26" width="200" height="64" as="geometry" />
                </mxCell>
            """
            output += node_text
            for target, edge_data in data['edges'].items():
                target_id = ""
                try:  # Check if target node is not in another flow
                    target_id = flow_data[target]['id']
                except KeyError:  # Search target node in another flows
                    for l_flow, f_data in graph.items():
                        try:
                            target_id = flow_data[target]['id']
                            break
                        except KeyError:
                            continue
                parsed = cst.parse_expression(edge_data['title'].replace('&quot;', '"'))
                if isinstance(parsed, cst.Call) and len(parsed.args) > 0  and isinstance(parsed.args[0].value, cst.List):
                    mod = cst.parse_module(edge_data['title'].replace('&quot;', '"'))
                    cndlist = [mod.code_for_node(el.value) for el in parsed.args[0].value.elements]
                    title = parsed.func.attr.value.capitalize().replace('"', '&quot;')
                else:
                    cndlist = []
                    title = edge_data['title']
                edge_text = f"""
                    <mxCell isedge="1" id="{edge_data['id']}" flow="{local_flow}" style="{edge_style}" parent="2" source="{data["id"]}" target="{edge_data['id'] + 1}" reallabel="{title}" realtarget="{target_id}" edge="1">
                        <mxGeometry relative="1" as="geometry">
                            <Array as="points">
                                <mxPoint x="150" y="{70 + y_shift}"/>
                                <mxPoint x="150" y="{70 + y_shift}"/>
                            </Array>
                        </mxGeometry>
                    </mxCell>
                    <mxCell id="{edge_data['id'] + 2}" flow="{local_flow}" style="{edge_style}" parent="2" source="{edge_data['id'] + 1}" target="{target_id}" edge="1">
                        <mxGeometry relative="1" as="geometry">
                            <Array as="points">
                                <mxPoint x="150" y="{70 + y_shift}"/>
                                <mxPoint x="150" y="{70 + y_shift}"/>
                            </Array>
                        </mxGeometry>
                    </mxCell>
                    <mxCell id="{edge_data['id'] + 1}" value="{title}" style="swimlane;fontColor=default;fontStyle=0;childLayout=stackLayout;horizontal=1;startSize=26;fillColor=#fff2cc;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;strokeColor=#d6b656;" vertex="1" parent="2" collapsed="1">
                          <mxGeometry x="150" y="{70 + y_shift}" width="200" height="26" as="geometry">
                              <mxRectangle x="10" y="40" width="200" height="90" as="alternateBounds" />
                          </mxGeometry>
                    </mxCell>
                """
                for cnd in cndlist:
                    edge_text += f"""
                        <mxCell parent="{edge_data['id'] + 1}" value="{cnd.replace('"', '&quot;')}" style="text;strokeColor=none;fontColor=default;fillColor=white;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontStyle=2;whiteSpace=wrap" vertex="1" >
                            <mxGeometry y="26" width="200" height="30" as="geometry" />
                        </mxCell>
                    """
                output += edge_text
        y_shift += 300
    output += tail
    return output


def pipeline(content):
    tree = ast.parse(content)
    flow = Flows(content, tree)
    nodes = flow2graph(flow)
    # from pprint import pprint
    # print(nodes)
    xml = graph2drawio(nodes, flow)
    return xml


content = sys.stdin.read()
data = pipeline(content)
sys.stdout.write(data)
