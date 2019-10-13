""" Convert flat node list into a call graph

    JSON file to Graphviz dot format
    https://www.graphviz.org/pdf/dotguide.pdf
"""
import argparse
import json
from call_graph import NodeType

from graphviz import Digraph


def validate_input():
    """ Assess command line arguments
    """
    # initiate the parser
    parser = argparse.ArgumentParser()

    """ Validate user input by verifying file can be opened, then close since this
        script only needs the filename.
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
        back to integer key
    """
    if isinstance(x, dict):
        try:
            # Key is an integer
            return {int(k):v for k,v in x.items()}
        except:
            # Key is a string
            return x
    return x


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
            print("Number of nodes loaded: " + str(len(self.nodes)) )

    def save(self):
        """ Save the internal call graph to file
        """
        with open( self.filename + '.json', 'w') as outfile:
            json.dump(self.call_graph, outfile, indent=4)


    def to_call_list(self):
        """ Generate an interal representation of a call graph
        """
        # For each root node (no caller), generate a call graph
        for key, node in self.nodes.items():
            if node['type'] == NodeType.function:
                #if key == 134272696: # TODO remove, used for debugging
                if not node['caller']:
                    # Found a root node
                    #print("Level: 0 " + node['name']) # TODO remove
                    level = 0
                    queue = {}
                    queue[level] = node['branch'].copy()

                    # Record root node
                    self.call_graph[key] = node
                    space = {}
                    space[level] = self.call_graph[key]
                    del space[level]['branch']
                    del space[level]['caller']
                    space[level]['level'] = level
                    space[level]['address'] = key

                    while ( queue[level] or level > 0):
                        if not queue[level]:
                            # Empty call list. 
                            # Step back one level and resume traversing list
                            level -= 1
                            continue

                        # Extract a node and traverse
                        _branch = queue[level].pop(0)
                        #print("Level: " + str(level + 1) + " " + self.nodes[_branch]['name']) # TODO remove

                        space[level][_branch] = self.nodes[_branch].copy()
                        del space[level][_branch]['branch']
                        del space[level][_branch]['caller']
                        space[level][_branch]['level'] = level + 1
                        space[level][_branch]['address'] = _branch # Used for recursion, TODO optimize

                        if self.nodes[_branch]['branch']:
                            # Edge node detected.
                            
                            # Check for direct or indirect recursion
                            is_recursion = False
                            if level > 0:
                                for __branch in self.nodes[_branch]['branch']:
                                    for key in range(0,level):
                                        if __branch == space[key]['address']:
                                            # Recursion detected
                                            # TODO need to insert into object for reporting
                                            print("    Recursion - " + self.nodes[__branch]['name'])
                                            is_recursion = True
                                            break
                                    else:
                                        continue  # only executed if the inner loop did NOT break
                                    break  # only executed if the inner loop DID break

                            if not is_recursion:
                                # Save new branch list for traversing
                                level += 1
                                queue[level] = self.nodes[_branch]['branch'].copy()

                                # Setup new reference to the last object inserted
                                space[level] = space[level - 1][_branch]

                            elif not queue[level]:
                                # Recursion detected.
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
    print("Format converter")
    filename = validate_input()

    nodes = Converter(filename)
    nodes.load()
    nodes.to_call_list()
    #nodes.to_dot() # TODO re-evaluate need to keep dot format
    nodes.save()
    

if __name__ == "__main__":
    main()



