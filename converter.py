""" Convert flat node list into a call graph

    JSON file to Graphviz dot format
    https://www.graphviz.org/pdf/dotguide.pdf
"""
import argparse
import json
from node_generator import NodeType
from pathlib import Path
from enum import auto, Enum

from graphviz import Digraph


class RecursionType(Enum):
    none = auto()
    direct = auto()
    indirect = auto()


def validate_input():
    """ Assess command line arguments
    """
    # initiate the parser
    parser = argparse.ArgumentParser()

    """ Validate user input by verifying file can be opened.
    """
    parser.add_argument('-i', '--infile', 
                        help="input file, JSON format", metavar="FILE",
                        type=argparse.FileType('r', encoding='UTF-8'), 
                        required=True)

    args = parser.parse_args()
    args.infile.close()

    return args.infile.name

def jsonKeys2int(x):
    """ JSON stores integer keys as a string. This method converts string
        back to integer key. Supports flat and nested dictionaries
    """
    return {int(k) if k.lstrip('-').isdigit() else k: v for k, v in x.items()}


class Converter:
    """ Converts nodes from a flat list into a call graph
    """
    def __init__(self, filename):
        self.filename = filename
        self.nodes = {}
        self.call_graph = {}

    def load(self):
        """ Gets the node list to be processed
        """
        with open(self.filename, 'r') as handle:
            self.nodes = json.load(handle, object_hook=jsonKeys2int)
        handle.close()
        print("Number of nodes loaded: " + str(len(self.nodes)) )        

    def save(self):
        """ Save the internal call graph to file
        """
        # Typical input filename would be 'something.node.json'
        # Expected output filename will be 'something.graph.json'
        fn = Path(self.filename)
        fn = fn.with_suffix('') # Remove '.json'
        fn = fn.with_suffix('.graph.json') # Replace '.node'

        print("Saving to file...", end="", flush=True)
        with open( fn, 'w') as outfile:
            json.dump(self.call_graph, outfile, indent=4)
        outfile.close()
        print("done.")

    def insert_branch_node(self, parent, level, child, recursion=RecursionType.none):
        """ Inserts a child (branch) node into its parent, nested dictionary
        """
        if recursion != RecursionType.direct:
            parent[level][child] = self.nodes[child].copy()
            del parent[level][child]['branch']
            del parent[level][child]['root']
            parent[level][child]['level'] = level + 1
            # TODO optimize, saving a redundant address inside the node
            # for use when assessing for recursion. Work around, because the
            # reference object does not have access to the node's key which is the
            # same value.
            parent[level][child]['address'] = child
            if recursion == RecursionType.none:
                parent[level][child]['recursion'] = False
            else:
                parent[level][child]['recursion'] = True
        
        if recursion != RecursionType.none:
            # Tag the active call path all the back to the root node with 
            # attribute 'recursion' set to True
            for index in range(0, level + 1):
                parent[index]['recursion'] = True


    def to_call_list(self):
        """ Generate an interal representation of a call graph
        """
        # For each root node, generate a call graph
        for key, node in self.nodes.items():
            if node['type'] == NodeType.function:
            #if key == 134272696: # TODO remove, single branch with one direct regression
            #if key == 134342576: # TODO remove, multi-branch with one direct regression
                if node['root']:
                    # Found a root node
                    #print("Level: 0 " + node['name']) # TODO remove
                    level = 0
                    queue = {}
                    queue[level] = node['branch'].copy()

                    # Record root node
                    self.call_graph[key] = node.copy()
                    space = {}
                    space[level] = self.call_graph[key]
                    del space[level]['branch']
                    del space[level]['root']
                    space[level]['level'] = level
                    space[level]['address'] = key
                    space[level]['recursion'] = False

                    while ( queue[level] or level > 0):
                        if not queue[level]:
                            # Empty call list. 
                            # Step back one level and resume traversing list
                            level -= 1
                            continue

                        # Extract a node for traversing
                        _branch = queue[level].pop(0)
                        #print("Level: " + str(level + 1) + " " + self.nodes[_branch]['name']) # TODO remove
                        
                        # Insert child node into parent node
                        self.insert_branch_node(space, level, _branch)

                        # Does the child node branch anywere
                        if self.nodes[_branch]['branch']:
                            # Edge node detected.
                            
                            # Check for direct or indirect recursion
                            recursion = RecursionType.none
                            queue[level + 1] = []
                            for __branch in self.nodes[_branch]['branch']:
                                recursion = RecursionType.none
                                for key in range(0,level + 1):
                                    if __branch == space[key]['address']:
                                        # Recursion detected
                                        if ( __branch == _branch ):
                                            recursion = RecursionType.direct
                                        else:
                                            recursion = RecursionType.indirect

                                        # Insert recursion branch 
                                        # directly into parent node, without traversing
                                        # 1. Advance reference to parent node
                                        # 2. Insert recursion branch
                                        # 3. Reset reference back to original state
                                        level += 1
                                        space[level] = space[level - 1][_branch]

                                        self.insert_branch_node(space, level, __branch, recursion)
                                        
                                        level -= 1

                                        # For direct recursion, branch path(s)
                                        # have already been analysed. Discard
                                        # pending information.
                                        if ( recursion == RecursionType.direct ):
                                            queue[level + 1] = []
                                            break

                                else:
                                    if recursion == RecursionType.none:
                                        # Save new branch for traversing
                                        queue[level + 1].append(__branch)
                                    continue  # only executed if the inner loop did NOT break
                                break  # only executed if the inner loop DID break


                            if recursion != RecursionType.direct:
                                # Setup new reference to the last object inserted
                                level += 1
                                space[level] = space[level - 1][_branch]

                            else:
                                # Direct recursion detected, treat as leaf node.
                                # Step back one level and resume traversing
                                if level > 0:
                                    level -= 1
                        elif not queue[level]:
                            # Leaf node detected, no branching. 
                            # Step back one level and resume traversing
                            if level > 0:
                                level -= 1



    def to_dot(self):
        """ Convert flat list into a dot format call graph
        """
        dot = Digraph(filename=self.filename + '.gv',
            node_attr={'color': 'lightblue2', 'style': 'filled'})

        # Create nodes, and link edges
        for key, node in self.nodes.items():
            if node['type'] == NodeType.function:
                # Create unique nodes using the key value, and label using
                # function name
                dot.node(str(key), label=node['name'])
                for branch in node['branch']:
                    dot.edge(str(key), str(branch))
        dot.save()


def main():
    print("Converter")
    filename = validate_input()

    nodes = Converter(filename)
    nodes.load()
    nodes.to_call_list()
    #nodes.to_dot() # TODO re-evaluate need to keep dot format
    nodes.save()
    

if __name__ == "__main__":
    main()



