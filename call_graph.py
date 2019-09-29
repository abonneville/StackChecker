""" Builds a call graph from a user provided ELF binary file, then saves the
    information to file. The output file is intended to be opend by an
    optional graph viewer.
"""
import argparse

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
    vtable = auto()
    assembly = auto()

tool_path = "C:\Program Files (x86)\Atollic\TrueSTUDIO for STM32 9.2.0\ARMTools\\bin\\"
tool_prefix = "arm-atollic-eabi-"
command = "objdump"

cmd = tool_path + tool_prefix + command



def is_valid_line(s):
    """ Evaluates if a string can be converted to a hexadecimal number.
    """
    try:
        int(s[0:9], 16)
        return True
    except ValueError:
        return False

def get_symbol_name(s):
    """ Returns the name of the symbol
        Must be qualified by calling is_valid_line()
    """
    begin = s.find('\t', 17)
    begin2 = s.find(' ', 17)
    if begin2 > begin:
        begin = begin2

    begin = s.find(' ', begin)
    begin += 1

    if begin != -1:
        return s[begin:]
    
    return ""



def is_function_start(s):
    """ Detects if the line indicates start of a new function
        valid:  123A <MySymbol>:
    """
    end = s.find(' ')
    qualifier = s.endswith(':')

    if end != -1 and qualifier:
        try:
            int(s[0:end], 16)
            return True
        except ValueError:
            return False

    return False

def get_function_addr(s):
    """ Returns the address of the function
        Must be qualified by calling is_function_start()
    """
    end = s.find(' ')

    try:
        return int(s[0:end], 16)
    except ValueError:
        return 0

def get_function_name(s):
    """ Returns the name of the function
        Must be qualified by calling is_function_start()
    """
    begin = s.find('<')
    end = s.rfind('>')

    if begin != -1 and end != -1:
        return s[begin + 1:end]
    
    return ""

def is_branch(s):
    """ Detects if the line contains a valid function call/branch
        valid: ... 123A <MySymbol>
        invalid:  ... <MySymbol+0x23>  <--local branch
        invalid:  .... (123A <MySymbol>)   <--reference to variable
    """
    begin = s.find('<')
    
    if begin != -1 and s.endswith('>'):
        if not('+0x' in s[begin:-1]) and not('-0x' in s[begin:-1]):
            return ( get_branch(s) != -1 )
    return False

def get_branch(s):
    """ Returns the address for the function called
        Must be qualified by calling is_branch()
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

def validate_input():
    # initiate the parser
    parser = argparse.ArgumentParser()

    """ Validate user input by verifying file can be opened, then close since this
        script only needs the filename.
    """
    parser.add_argument('-i', '--infile', 
                        help="input file, ELF format", metavar="FILE",
                        type=argparse.FileType('r', encoding='UTF-8'), 
                        required=True)

    args = parser.parse_args()
    args.infile.close()

    return args.infile.name




class Node():
    """ Each node represents a function or object used in a call graph.
    """
    
    def __init__(self, filename):
        self.nodes = {}
        self.filename = filename

    def get_symbols(self):
        """ Creates a raw symbol list from the user provided input file
        """
        terminal = subprocess.Popen([cmd, '--syms', '--demangle', 
                            self.filename ], shell=True, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        stdout, stderr = terminal.communicate()
        stdout = str(stdout, encoding='utf-8')
        lines = stdout.splitlines()

        return lines

    def get_disassembly(self):
        """ Disassemble the user provided input file
        """
        terminal = subprocess.Popen([cmd, '--disassemble-all', '--demangle', 
                            self.filename ], shell=True, 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
        stdout, stderr = terminal.communicate()
        stdout = str(stdout, encoding='utf-8')
        lines = stdout.splitlines()
        return lines


    def save(self):
        """ Save all nodes to file
        """
        with open( self.filename + '.json', 'w') as outfile:
            json.dump(self.nodes, outfile, indent=4)


    def build(self):
        """ Establish each node
        """
        lines = self.get_symbols()

        for line in lines:
            address = 0
            if( is_valid_line(line[0:8]) ):
                node = {}

                node['name'] = get_symbol_name(line)

                """ These data columns are variable length word(s).
                    TODO re-implement as method call to get string
                """
                words = line[17:].split()
                node['section'] = words[0]
                node['size'] = int(words[1], 16)

                """ Colmun(s) at the beginning of the line are fixed width.
                """

                """ The input file contains a collection of all symbols; data, 
                    functions, etc...
                """
                if line[NodeType.index] == 'F':
                    node['type'] = NodeType.function
                elif line[NodeType.index] == 'O':
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
                            node['type'] = NodeType.assembly
                        

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

                node['caller'] = []
                node['branch'] = []

                # Symbol address will become the node key, and therefore must
                # be unique for each entry.
                end = line.find(' ')
                address = int(line[0:end], 16)

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
        assembly_node = 0
        unknown_node = 0
        
        for key, node in self.nodes.items():

            if node['type'] == NodeType.function:
                function_node += 1

                if not node['caller']:
                    root_node += 1
                
                if not node['branch']:
                    leaf_node += 1
                
                if not node['branch'] and not node['caller']:
                    free_node += 1

            if node['type'] == NodeType.filename:
                filename += 1

            if node['type'] == NodeType.obj:
                obj_node += 1

            if node['type'] == NodeType.unknown:
                unknown_node += 1
            
            if node['type'] == NodeType.assembly:
                assembly_node += 1

        print("\nFunction , total: " + str(function_node) )
        print("Filename , total: " + str(filename) )
        print("Object   , total: " + str(obj_node) )
        print("Assembly , total: " + str(assembly_node))
        print("Unknown  , total: " + str(unknown_node) )
        print("All nodes, total: " + str(self.nodes.__len__()) )
        print("\nRoot func, total: " + str(root_node) )
        print("Leaf func, total: " + str(leaf_node) )
        print("Free func, total: " + str(free_node) )


    def link(self):
        """ Updates an existing node list with a node's caller and branch list
        """
        lines = self.get_disassembly()

        in_progress = False
        address = 0

        for line in lines:
            if is_function_start(line):
                # New function detected
                address = get_function_addr(line)
                if ( address in self.nodes):
                    in_progress = True
                    self.nodes[address]['branch'] = []
                else:
                    in_progress = False
                    print("Missing function: " + line)

            elif is_branch(line) and in_progress:
                # New branch detected
                target = get_branch(line)
                if ( target in self.nodes):
                    self.nodes[address]['branch'].append(target)
                    self.nodes[target]['caller'].append(address)
                else:
                    print("Missing branch: " + line)



def main():
    print("Stack Checker")
    filename = validate_input()

    nodes = Node(filename)
    nodes.build()
    nodes.link()
    nodes.show_node_metrics()
    nodes.save()


if __name__ == "__main__":
    main()
