import base64
import json
import ast
import sys
from lxml import etree


class SFC:
    def __init__(self, func):
        self.func = func.replace("('", "(\"").replace("')", "\")")
        try:
            ast.parse(self.func)
        except SyntaxError:  # Reseived argument is not a function. Convert to string
            self.func = f'"{self.func}"'

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
        if node.tag == 'UserObject':
            nodes[int(node.attrib['id'])] = {
                'title': node.attrib['label'], 'node': node}
        elif node.tag == 'mxCell':
            try:
                node.attrib['style']
            except KeyError:  # Not an arrow
                continue
            try:
                edges[int(node.attrib['source'])]
            except KeyError:
                edges[int(node.attrib['source'])] = {}
            edges[int(node.attrib['source'])][int(
                node.attrib['target'])] = node.attrib['value']
    return nodes, edges


def graph2flow(nodes, edges):
    flow = {}
    for node_dict in nodes.values():
        node = node_dict['node']
        transitions = {}
        for edge, edge_title in edges[int(node.attrib['id'])].items():
            transitions[nodes[edge]['title']] = SFC(edge_title)
        processing = ast.literal_eval(node.attrib['processing'])
        for id_, func_list in processing.items():
            for i in range(len(func_list)):
                func_list[i] = Processing(func_list[i])
        node_data = f"""'{node.attrib['label']}': {{
            TRANSITIONS: {str(transitions)},
            PROCESSING: {str(processing)},
            RESPONSE: "{node.attrib['response']}"
            }}"""
        try:  # Check if flow not exists
            flow[node.attrib['flow']]
        except KeyError:
            flow[node.attrib['flow']] = []
        flow[node.attrib['flow']].append(node_data)
    return flow


def pretty_print(flow):
    output = ""
    head = """flows = {
    GLOBAL: {
        TRANSITIONS: {},
        PROCESSING: {},
        RESPONSE: {},
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
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.Dict):
                    for key in child.keys:
                        if isinstance(key, ast.Name):
                            if key.id == "GLOBAL":
                                return ast.get_source_segment(content, node)
    return None


def pipeline(content):
    nodes, edges = parse_file(content)
    flow = graph2flow(nodes, edges)
    output = pretty_print(flow)
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
