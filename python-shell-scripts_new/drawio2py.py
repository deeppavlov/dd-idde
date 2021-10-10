import base64
import json
import ast
import sys
from lxml import etree


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
                self.func = f'cnd.all([custom_functions.speech_functions("{self.func}")])'
        else:
            self.func = '""'

    def __repr__(self):
        return str(self.func)


class Processing:
    def __init__(self, func):
        self.func = func

    def __repr__(self):
        return str(self.func)


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


def graph2flow(nodes, edges):
    flow = {}
    for node_dict in nodes.values():
        node = node_dict['node']
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
        # Check Processing
        try:
            processing = ast.literal_eval(node.attrib['processing'])
        except KeyError:
            processing = {}
        for id_, func_list in processing.items():
            for i in range(len(func_list)):
                func_list[i] = Processing(func_list[i])
        # Check Response
        try:
            response = node.attrib['response']
        except KeyError:
            response = ""
        if sfc:
            node_data = f""""{node_name}": {{
                TRANSITIONS: {str(transitions)},
                PROCESSING: {str(processing)},
                RESPONSE: "{response}",
                MISC: {{"speech_functions": ["{sfc}"]}}
                }}"""
        else:
            node_data = f""""{node_name}": {{
                TRANSITIONS: {str(transitions)},
                PROCESSING: {str(processing)},
                RESPONSE: "{response}"
                }}"""
        try:  # Check if flow not exists
            flow[node.attrib['flow']]
        except KeyError:
            flow[node.attrib['flow']] = []
        flow[node.attrib['flow']].append(node_data)
    return flow


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


def pretty_print(flow, flows_name):
    if flows_name:  # If we have name of flows variable, then use it; else "flows"
        var = flows_name
    else:
        var = "flows"
    output = ""
    head = """flows = {
    GLOBAL: {
        TRANSITIONS: {},
        PROCESSING: {},
        RESPONSE: {},
        MISC: {}
    },\n\t"""
    output += head
    for name, content in flow.items():
        output += f'"{name}": {{\n\t\t'
        content = ",\n\t\t".join(content)
        output += content + "\n\t\t},\n\t"
    tail = """\n}"""
    output += tail
    return output


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
    flow = graph2flow(nodes, edges)
    output = pretty_print(flow, flows_name)
    return output


# Receiving data from Extension (JSON: { 'xmlData': ..., 'pyData': .... })
extensionData = sys.stdin.read()
extensionDataDict = json.loads(extensionData)
pythonCode = extensionDataDict['pyData']
# Parse old Python code to find node with Flow data
pyAstTree = ast.parse(pythonCode)
flowToReplace = find_flow(pythonCode, pyAstTree)
# Convert Drawio content to Python dict
newFlow = pipeline(extensionDataDict['xmlData'])
# Replace old Flow with converted data from XML
pythonCode = pythonCode.replace(flowToReplace, newFlow)

base64response = base64.b64encode(bytes(pythonCode, 'utf-8')).decode('utf-8')
response = json.dumps({'pyCode': base64response})
sys.stdout.write(response)
# print(str(pythonCode))
