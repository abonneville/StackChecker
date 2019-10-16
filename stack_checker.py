""" Front-end for collecting user input, processing binary data, and displaying
    call and stack information to user.
"""

import argparse
from pathlib import Path

from node_generator import Node, parent_parser
from converter import Converter
from viewer import Viewer


class StackChecker:
    def __init__(self):
        self.infile = Path()
        self.objdump = Path()
        self.output_path = Path()
        self.stack_path = Path()
        self.vector =""

    def cli(self):
        """ Process user input from the command line.
        """
        cli_parser = argparse.ArgumentParser(
            parents=[parent_parser],
            fromfile_prefix_chars="@",
            description="Analysis binary code and display stack & call information."
            )

        args = cli_parser.parse_args()

        # Input file will be processed directly by objdump utility, just 
        # validate user input file is readable and close.
        args.infile.close()

        # Set internal references
        # TODO need to validate user input, directory(s) exist or need to be
        # created
        self.infile = Path(args.infile.name).absolute()
        self.objdump = args.tool_objdump
        self.output_path = args.output_path
        self.stack_path = args.stack_path
        self.vector = args.vector

def main():
    """ Runs the required scripts and coordinates exchange of data
    """
    stack = StackChecker()
    stack.cli()

    # Generate node flat list
    print("Generating node list...", end="", flush=True)
    nodes = Node(stack.objdump, stack.infile, stack.vector, stack.stack_path, stack.output_path)
    nodes.build()
    nodes.link()
    print("done.")    
    #nodes.show_node_metrics()

    # Generate call graph
    print("Generating call graph...", end="", flush=True)
    graph = Converter()
    graph.set_nodes( nodes.get_nodes() )
    graph.to_call_list()
    print("done.")    

    # Launch viewer
    print("Launching viewer...")
    viewer = Viewer()
    viewer.set_graph( graph.get_graph() )
    viewer.show()


if __name__ == "__main__":
    main()
    