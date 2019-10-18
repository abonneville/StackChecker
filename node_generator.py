""" Builds a node list from a user provided ELF binary file, then saves the
    information to file.
"""
import argparse
from pathlib import Path

import json

from enum import auto, IntEnum

import subprocess, sys


class SymbolScope(IntEnum):
    index = 9
    none = auto()
    local = auto()
    glb = auto()
    un_glb = auto()
    error = auto()

class SymbolMessage(IntEnum):
    index = 12
    none = auto()
    warning = auto()

class NodeType(IntEnum):
    index = 15
    unknown = auto()
    function = auto()
    filename = auto()
    obj = auto()
    dispatch_table = auto()
    vector_table = auto()
    vtable = auto()


parent_parser = argparse.ArgumentParser(
    add_help=False,
    fromfile_prefix_chars="@"
    )

parent_parser.add_argument('-i', '--infile', required=True,
    type=argparse.FileType('r', encoding='UTF-8'), 
    help="Source binary file, ELF format"
    )

parent_parser.add_argument('-to', '--tool_objdump', nargs='?',
    type=lambda p: Path(p).absolute(),
    default="objdump.exe",
    help='File to be used for objdump utility'
    )

parent_parser.add_argument('-op', '--output_path', nargs='?',
    type=lambda p: Path(p).absolute(),
    default=Path(__file__).absolute().parent / "sc-output",
    help='Directory to store output files'
    )

parent_parser.add_argument('-sp', '--stack_path', nargs='*', 
    type=lambda p: Path(p).absolute(),
    default=Path(__file__).absolute().parent,
    help='Directory(s) to obtain stack usage (*.su) file(s)'
    )

parent_parser.add_argument("-v", "--vector", nargs='?',
    default="",
    help="Symbol that identifies a vector table for ISRs")



def is_symbol_line(s):
    """ Determines if the line contains a symbol
    """
    # A tab is the central reference point for slicing the line in later 
    # operations. Verify it is present, and that only one exists per line.
    qualifier1 = s.find('\t')
    qualifier2 = s.rfind('\t')
    if qualifier1 == -1 or qualifier1 != qualifier2:
        return False

    return True

def get_symbol_address(s):
    """ Returns symbol address in decimal form
        Must be qualified by calling is_symbol_line()
    """
    end = s.find(' ')
    return int(s[0:end], 16)


def get_symbol_name(s):
    """ Returns the name of the symbol
        Must be qualified by calling is_symbol_line()
    """
    begin = s.find('\t')
    if begin != -1:
        begin = s.find(' ', begin)

    if begin != -1:
        begin += 1
        return s[begin:]
    
    return ""

def get_symbol_section(s):
    """ Returns the name of the section the symbol resides in
        Must be qualified by calling is_symbol_line()
    """
    begin = -1
    end = s.find('\t')
    if end != -1:
        begin = s.rfind(' ', 0, end)

    if begin != -1:
        begin += 1
        return s[begin:end]

    return ""


def get_symbol_size(s):
    """ Returns the size of memory (in bytes) the symbol represents
        Must be qualified by calling is_symbol_line()
    """
    end = -1
    begin = s.find('\t')
    if begin != -1:
        end = s.find(' ', begin)

    if begin != -1 and end != -1:
        begin += 1
        return int(s[begin:end], 16)

    return 0

def is_node_start(s):
    """ Detects if the line indicates start of a new noe
        valid:  123A <MySymbol>:
    """
    end = s.find(' ')
    qualifier = s.endswith(':') and not('+0x' in s) and not('-0x' in s)

    if end != -1 and qualifier:
        try:
            int(s[0:end], 16)
            return True
        except ValueError:
            return False
    return False

def get_node_address(s):
    """ Returns the address of the node
        Must be qualified by calling is_node_start()
    """
    end = s.find(' ')

    try:
        return int(s[0:end], 16)
    except ValueError:
        return 0

def get_line_address(s, terminator):
    """ Returns the address at the start of the line
        Must be qualified by calling is_node_start()
    """
    end = s.find(terminator)

    try:
        return int(s[0:end], 16)
    except ValueError:
        return 0



def is_node_branch(s):
    """ Detects if the line contains a valid node call/branch
        valid: ... 123A <MySymbol>
        invalid:  ... <MySymbol+0x23>  <--local branch
        invalid:  .... (123A <MySymbol>)   <--reference to variable
    """
    begin = s.find('<')
    
    if begin != -1 and s.endswith('>'):
        qualifier = not('+0x' in s[begin:-1]) and not('-0x' in s[begin:-1])
        if qualifier:
            return ( get_branch_address(s) != -1 )
    return False

def get_branch_address(s):
    """ Returns the address for the branch
        Must be qualified by calling is_node_branch()
    """
    begin = -1
    end = s.rfind(' <')
    if end != -1:
        begin = s.rfind('\t',0,end)
        begin2 = s.rfind(' ',0,end)
        if begin2 > begin:
            begin = begin2

    if begin != -1 and end != -1:
        try:
            return int(s[begin:end], 16)
        except ValueError:
            return -1
    else:
        return -1

def get_pointer(s):
    begin = s.find('\t')
    end = s.find(' ', begin)

    if begin != -1 and end != -1:
        begin += 1
        try:
            return int(s[begin:end], 16)
        except:
            return -1
    else:
        return -1





class Node():
    """ Each node represents a function or object used in a call graph.
    """
    
    def __init__(self, objdump=Path(), infile=Path(), vector="", stack_path=Path(), output_path=('.')):
        self.nodes = {}
        self.dispatch_table = {}

        self.objdump = Path(objdump)
        self.infile = Path(infile).absolute()
        self.vector_table = vector
        self.stack_path = Path(stack_path)
        self.output_path = Path(output_path)

    def cli(self):
        """ Process user input from the command line.
        """
        cli_parser = argparse.ArgumentParser(
            parents=[parent_parser],
            fromfile_prefix_chars="@",
            description="Analysis binary code for stack and call information."
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
        self.vector_table = args.vector

    def get_symbols(self):
        """ Creates a raw symbol list from the user provided input file
        """
        terminal = subprocess.Popen([str(self.objdump), '--syms', '--demangle', 
                            str(self.infile) ], shell=True, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        stdout, stderr = terminal.communicate()
        stdout = str(stdout, encoding='utf-8')
        lines = stdout.splitlines()

        return lines

    def get_disassembly(self):
        """ Disassemble the user provided input file
        """
        terminal = subprocess.Popen([str(self.objdump), '--disassemble-all', '--demangle', 
                            str(self.infile) ], shell=True, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        stdout, stderr = terminal.communicate()
        stdout = str(stdout, encoding='utf-8')
        lines = stdout.splitlines()
        return lines

    def get_nodes(self):
        """ Return reference to internal node list
        """
        return self.nodes


    def save(self):
        """ Save all nodes to file
        """
        fn = Path(self.infile)
        with open( fn.with_suffix('.node.json'), 'w') as outfile:
            json.dump(self.nodes, outfile, indent=4)
        outfile.close()


    def build(self):
        """ Establish each node
        """
        lines = self.get_symbols()

        for line in lines:
            address = 0
            if( is_symbol_line(line) ):
                node = {}

                node['name'] = get_symbol_name(line)

                node['section'] = get_symbol_section(line)
                node['size'] = get_symbol_size(line)

                """ The input file contains a collection of all symbols; data, 
                    functions, etc...
                """
                if line[NodeType.index] == 'F':
                    node['type'] = NodeType.function
                elif line[NodeType.index] == 'O':
                    if node['name'] == self.vector_table:
                        node['type'] = NodeType.vector_table
                    else:
                        node['type'] = NodeType.obj

                elif line[NodeType.index] == ' ':
                    # Functions implemented in assembly code get lumped in 
                    # here. 
                    if '.' in node['name']:
                        # Discard, periods are not allowed in function names
                        continue
                    else:
                        # TODO need to make section user definable
                        if node['section'] != '.text':
                            # Discard, invalid section
                            continue
                        else:
                            node['type'] = NodeType.function
                        

                else:
                    # All other symbols for filename, debug info, etc... are
                    # not guaranteed to have a unique address (key), and 
                    # therefore cannot be logged. 
                    continue

                # Decode the symbol scope
                if line[SymbolScope.index] == 'l':
                    node['scope'] = SymbolScope.local
                elif line[SymbolScope.index] == 'g':
                    node['scope'] = SymbolScope.glb
                elif line[SymbolScope.index] == 'u':
                    node['scope'] = SymbolScope.un_glb
                elif line[SymbolScope.index] == '!':
                    node['scope'] = SymbolScope.error
                else:
                    node['scope'] = SymbolScope.none

                """ TODO delete
                if line[SymbolMessage.index] == 'W':
                    node['message'] = SymbolMessage.warning
                else:
                    node['message'] = SymbolMessage.none

                """

                node['root'] = True
                node['branch'] = []

                # Symbol address will become the node key, and therefore must
                # be unique for each entry.
                address = get_symbol_address(line)
                self.nodes[address] = node
        
        
    def show_node_metrics(self):
        """ Displays node summary information.
        """
        leaf_node = 0 # edge of tree
        free_node = 0 # neither leaf or root, floating
        root_node = 0 # base of tree
        function_node = 0
        filename = 0
        obj_node = 0
        unknown_node = 0
        vector_table = 0
        
        for node in self.nodes.values():

            if node['type'] == NodeType.function:
                function_node += 1

                if not node['branch'] and node['root']:
                    free_node += 1

                elif node['root']:
                    root_node += 1
                
                elif not node['branch']:
                    leaf_node += 1
                

            if node['type'] == NodeType.filename:
                filename += 1

            if node['type'] == NodeType.obj:
                obj_node += 1

            if node['type'] == NodeType.unknown:
                unknown_node += 1
            
            if node['type'] == NodeType.vector_table:
                vector_table += 1
            

        print("\nFunction , total: " + str(function_node) )
        print("Filename , total: " + str(filename) )
        print("Object   , total: " + str(obj_node) )
        print("Vector   , total: " + str(vector_table) )
        print("Unknown  , total: " + str(unknown_node) )
        print("All nodes, total: " + str(self.nodes.__len__()) )
        print("\nRoot func, total: " + str(root_node) )
        print("Leaf func, total: " + str(leaf_node) )
        print("Free func, total: " + str(free_node) )

    def set_dispatch(self, lines):
        """ Evaluates all object nodes, if function poiners are found then
            defines object as a dispatch table and records table entries.
        """
        in_progress = False

        for line in lines:
            table = {}
            
            if is_node_start(line):
                # Start of node detected
                address = get_node_address(line)
                in_progress = False

                if ( address in self.nodes):
                    if self.nodes[address]['type'] == NodeType.obj:
                        in_progress = True

            elif in_progress:
                # Evaluate for dispatch table entry(s)
                target = get_pointer(line)
                if target != -1:
                    if ( target in self.nodes):
                        if self.nodes[target]['type'] == NodeType.function:
                            # ARM state
                            table['function'] = target
                            table['table'] = address
                            line_address = get_line_address(line, ':')
                            self.dispatch_table[line_address] = table
                    elif ( target - 1 in self.nodes):
                        if self.nodes[target - 1]['type'] == NodeType.function:
                            # Thumb state
                            table['function'] = target - 1
                            table['table'] = address
                            line_address = get_line_address(line, ':')
                            self.dispatch_table[line_address] = table

    def link_to_function(self, parent, child):
        """ Evaluates if the child is a valid address to a function, and if so,
            links the parent to the child node.
        """
        if child != -1:
            # Convert thumb (odd) to ARM (even) state
            child = child if child % 2 == 0 else child - 1
            if child in self.nodes:
                if self.nodes[child]['type'] == NodeType.function:
                    if ( not child in self.nodes[parent]['branch'] ):
                        # For optimization, we only record unique branches
                        self.nodes[parent]['branch'].append(child)
                        self.nodes[child]['root'] = False

    def link(self):
        """ Updates an existing node list with a node's branch list
        """
        lines = self.get_disassembly()

        self.set_dispatch(lines)

        in_progress = False
        address = 0
        node_type  = NodeType.unknown

        function = {} # list, link to reference table(s)
        reference = {} # list,  link to dispatch table(s)
        dispatch = {} # list, table of function pointers

        for line in lines:
            if is_node_start(line):
                # Start of node detected
                address = get_node_address(line)
                if ( address in self.nodes):
                    node_type = self.nodes[address]['type']
                    in_progress = True
                    self.nodes[address]['branch'] = []
                else:
                    in_progress = False
                    # TODO log print("Missing node: " + line)

            elif node_type == NodeType.function and in_progress:
                if is_node_branch(line):
                    # Branch detected
                    target = get_branch_address(line)
                    self.link_to_function(address, target)

                else:
                    target = get_pointer(line)
                    if target != -1:
                        # Convert thumb (odd) to ARM (even) state
                        target = target if target % 2 == 0 else target - 1
                        if target in self.dispatch_table:
                            # Evaluate for accessing dispatch table (function pointer)
                            function.setdefault(address, []).append(target)

                        elif target in self.nodes:
                            # Evaluate accessing function poiners directly
                            #
                            # Note: this discovers referencing functions
                            # dynamically, such as setting a reference to.
                            # The function is not actually called.
                            if self.nodes[target]['type'] == NodeType.function:
                                pass
                                #print( self.nodes[address]['name'] + " ---- ", end="")
                                #print( self.nodes[target]['name'] )
             
            elif node_type == NodeType.obj and in_progress:
                # Evaluate for dispatch table entry(s)
                target = get_pointer(line)
                if target != -1:
                    if ( target in self.dispatch_table):
                        # Indirect reference table to the dispatch table
                        #print(self.nodes[address]['name'] + " --- " + self.nodes[target]['name'])
                        reference.setdefault(address, []).append(target)
                    elif ( target - 1 in self.nodes):
                        #target -= 1  #TODO specific to thumb-2 mode, read ELF first
                        #print(self.nodes[address]['name'] + " --- " + self.nodes[target]['name'])
                        dispatch.setdefault(address, []).append(target - 1)
                        

            elif node_type == NodeType.vector_table and in_progress:
                # Map function pointer calls
                target = get_pointer(line)
                self.link_to_function(address, target)


        # Function link --> Reference Table --> Dispatch Table --> Function()
        # TODO issue, cannot directly access initial offset value to determine
        # which pointer is being accessed. Its in the disassembly code, but not
        # a line descriptor. 
        
        """
        for method, ref in function.items():
            print(self.nodes[method]['name'])
            for _ref in ref:
                for _reference, xref in reference.items():
                    if _ref == _reference:
                        #print("i am here")
                        #print(self.nodes[_reference]['name'])
                        for _xref in xref:
                            for _dispatch, ptr in dispatch.items():
                                if _xref == _dispatch:
                                    #if _ptr in self.nodes:
                                    print("  " + self.nodes[_ref]['name'] + " --- " + self.nodes[_dispatch]['name'] + "  size: " + str( len(ptr)) )
        """

        """ For function pointers in the first degree and a dispatch table size 
            of 1, the following will map simple function pointers.
        """ 
        """
        node_count = 0
        for _dispatch, ptr in dispatch.items():
            for method, ref in function.items():
                for _ref in ref:
                    if _ref == _dispatch:
                        node_count += 1
                        print(self.nodes[method]['name'] + " --- " + self.nodes[_dispatch]['name'] + "  size: " + str( len(ptr)) )
                        for _ptr in ptr:
                            print("  " + self.nodes[_ptr]['name'] )
        print("\nFunction pointers, 1st degree")
        print("Matches: " + str(node_count) )
        """

        """ For function pointers in the first degree and a dispatch table size 
            of 1, the following will map simple function pointers.
        """ 
        
        """
        # Displays all functions that directly reference a dispatch table
        node_count = 0
        for method, ref in function.items():
            for _ref in ref:
                    if _ref in self.dispatch_table:
                        node_count += 1
                        ptr = self.dispatch_table[_ref]
                        print(self.nodes[method]['name'] + " --- " + self.nodes[ptr['table'] ]['name'] + " " + str(self.nodes[ptr['table'] ]['size']) )
                        print("  " + self.nodes[ptr['function'] ]['name'] )
                    else:
                        print("\n **** Error: unable to find entry in dispatch table **** \n")

        print("\nFunction pointers")
        print("References, 1st Degree: " + str(node_count) )
        print("All, total: " + str(self.dispatch_table.__len__()) )

        print("References, 2nd degree")
        for key, table in reference.items():
            print(self.nodes[key]['name'] + " --- " ) #+ self.nodes[table[0]]['name'])
        """
        
        #print("All function pointers")
        #for key, ptr in self.dispatch_table.items():
        #    print(self.nodes[ ptr['table'] ]['name'] + " ---- " + self.nodes[ ptr['function'] ]['name'])

        """ Display all dispatch tables and associated function pointers
        """
        """
        node_count = 0
        unique_nodes = {}
        for _dispatch, ptr in dispatch.items():
            print(self.nodes[_dispatch]['name'])
            for _ptr in ptr:
                if not _ptr in unique_nodes:
                    unique_nodes[_ptr] = 0
                    node_count += 1
                print("  " + self.nodes[_ptr]['name'] )
        print("\nUnique function pointers, total " + str(node_count) )
        """

def main():
    print("Node generator")

    nodes = Node()
    nodes.cli()
    nodes.build()
    nodes.link()
    nodes.show_node_metrics()
    nodes.save()


if __name__ == "__main__":
    main()
