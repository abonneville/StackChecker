"""
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

class SymbolType(IntEnum):
    index = 15
    none = auto()
    function = auto()
    filename = auto()
    obj = auto()

class NodeType(IntEnum):
    unknown = auto()
    function = auto()
    dispatch_table = auto()
    vtable = auto()

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
    #end = s.rfind('>')
    #qualifier = s.find('(')
    
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



def build_symbols(filename):
    """ Analysis the binary input file and create an internal list of symbols.
    """
    terminal = subprocess.Popen([cmd, '--syms', '--demangle', filename ], shell=True, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
    stdout, stderr = terminal.communicate()
    lines = stdout.splitlines()

    nodes = []
    for line in lines:
        node = {}
        if( is_valid_line(line[0:8]) ):

            """ Colmun(s) at the beginning of the line are fixed width.
            """

            """ The input file contains a collection of all symbols. Record only
                functions and discard all other symbols.

                TODO - for evaluation, record all symbols and optimize later
            """
            if line[SymbolType.index] == ord('F'):
                node['type'] = SymbolType.function
            elif line[SymbolType.index] == ord('f'):
                node['type'] = SymbolType.filename
            elif line[SymbolType.index] == ord('O'):
                node['type'] = SymbolType.obj
            else:
                node['type'] = SymbolType.none

            # Grab 32-bit address
            node['address'] = line[0:8]

            # Decode the symbol formatting
            if line[SymbolScope.index] == ord('l'):
                node['scope'] = SymbolScope.local
            elif line[SymbolScope.index] == ord('g'):
                node['scope'] = SymbolScope.glb
            elif line[SymbolScope.index] == ord('u'):
                node['scope'] = SymbolScope.un_glb
            elif line[SymbolScope.index] == ord('!'):
                node['scope'] = SymbolScope.error
            else:
                node['scope'] = SymbolScope.none

            if line[SymbolMessage.index] == ord('W'):
                node['message'] = SymbolMessage.warning
            else:
                node['message'] = SymbolMessage.none


            """ The remainder of the columns are variable length word(s).
            """
            words = line[17:].split()
            node['section'] = words[0]
            node['size'] = int(words[1], 16)
            try:
                # Test, because some lines are missing the last field.
                # Column width is 1 or more bytes
                node['name'] = words[2:]
            except IndexError:
                # Column width is 0 bytes
                node['name'] = ""

            nodes.append(node)


def build_symbol_table(symbols, filename):
    """ Analysis the binary input file and create an internal list of symbols.
    """
    terminal = subprocess.Popen([cmd, '--syms', '--demangle', filename ], shell=True, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
    stdout, stderr = terminal.communicate()
    lines = stdout.splitlines()

    for line in lines:
        address = 0
        if( is_valid_line(line[0:8]) ):
            symbol = {}

            """ Colmun(s) at the beginning of the line are fixed width.
            """

            """ The input file contains a collection of all symbols; data, 
                functions, etc...
            """
            if line[SymbolType.index] == ord('F'):
                symbol['type'] = SymbolType.function
            elif line[SymbolType.index] == ord('f'):
                symbol['type'] = SymbolType.filename
            elif line[SymbolType.index] == ord('O'):
                symbol['type'] = SymbolType.obj
            else:
                symbol['type'] = SymbolType.none

            # Grab 32-bit address
            address = int(line[0:8], 16)

            # Decode the symbol formatting
            if line[SymbolScope.index] == ord('l'):
                symbol['scope'] = SymbolScope.local
            elif line[SymbolScope.index] == ord('g'):
                symbol['scope'] = SymbolScope.glb
            elif line[SymbolScope.index] == ord('u'):
                symbol['scope'] = SymbolScope.un_glb
            elif line[SymbolScope.index] == ord('!'):
                symbol['scope'] = SymbolScope.error
            else:
                symbol['scope'] = SymbolScope.none

            if line[SymbolMessage.index] == ord('W'):
                symbol['message'] = SymbolMessage.warning
            else:
                symbol['message'] = SymbolMessage.none


            """ The remainder of the columns are variable length word(s).
            """
            words = line[17:].split()
            symbol['section'] = words[0]
            symbol['size'] = int(words[1], 16)
            try:
                # Test, because some lines are missing the last field.
                # Column width is 1 or more bytes
                symbol['name'] = words[2:]
            except IndexError:
                # Column width is 0 bytes
                symbol['name'] = ""

            symbols[address] = symbol
        
        


def build_nodes(lines):
    """ Returns a raw list of nodes. Upon completion each node knows who they
        call.
    """
    nodes = {}
    
    in_progress = False
    address = 0

    for line in lines:
        if is_function_start(line):
            # New function detected
            if in_progress:
                # Log previous node
                node['branch'] = branch
                nodes[address] = node

            in_progress = True
            node = {}
            branch = []
            address = get_function_addr(line)
            node['name'] = get_function_name(line)
            node['type'] = NodeType.unknown
            node['caller'] = []

        elif is_branch(line) and in_progress:
            # New branch detected, log callee
            branch.append(get_branch(line) )

    # Search is complete
    if in_progress:
        # Log last node detected
        node['branch'] = branch
        nodes[address] = node

    return nodes

def set_node_caller(nodes):
    """ Upon entry, each node knows who they call.
        Walk through the list and update each node with a list of who calls
        them.
    """
    for caller, node in nodes.items():
        for branch in node['branch']:
            try:
                nodes[branch]['caller'].append(caller)
            except KeyError:
                print("Missing node called by: " + node['name'])


def set_node_info(symbols, nodes):
    
    for key, symbol in symbols.items():
        if (symbol['type']) == SymbolType.function:
            try:
                nodes[key]['type'] = NodeType.function
            except KeyError:
                print("Missing function node: " + symbol['name'])




def set_dispatch_tables(nodes, lines):
    """ Upon entry, any free nodes (no caller or branch defined) are potential
        dispatch tables containing function pointers. Locate dispatch tables
        and create linkage between function nodes.
    """
    for key, node in nodes.items():
        # Locate free nodes
        if not node['branch'] and not node['caller']:
            """ Found a free node.
                
                Now locate any references to it,  indicating its a jump table
            """
            print(node)


def show_node_metrics(nodes):
    """ Displays node summary information.
    """
    leaf_node = 0 # edge of tree
    free_node = 0 # neither leaf or root, floating
    root_node = 0 # base of tree
    unknown_node = 0
    
    for key, node in nodes.items():
        if not node['caller']:
            root_node += 1
        
        if not node['branch']:
            leaf_node += 1
        
        if not node['branch'] and not node['caller']:
            free_node += 1

        if node['type'] == NodeType.unknown:
            unknown_node += 1

    print("Root node, total: " + str(root_node) )
    print("Leaf node, total: " + str(leaf_node) )
    print("Free node, total: " + str(free_node) )
    print("Unknown, total: " + str(unknown_node) )
    print("All nodes, total: " + str(nodes.__len__()) )


def build_call_tree(symbols, filename):
    """ Analysis the binary input file and create linkage between symbols (i.e. 
    call tree).
    """
    
    terminal = subprocess.Popen([cmd, '--disassemble-all', '--demangle', 
                        #'--start-address=0x08000000', 
                        #'--stop-address=0x08001000',
                        filename ], shell=True, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
    stdout, stderr = terminal.communicate()
    #stdout = literal_eval(stdout.decode('UTF-8'))
    #lines = x.splitlines()
    stdout = str(stdout, encoding='utf-8')
    lines = stdout.splitlines()
    #print(lines)

    """ Start by parsing the file to discover all possible nodes (functions).
        Initially, each node is assumed to be a root node. Next, build branches
        by discovering which nodes are not a root node. When completed 
        remaining list of root nodes are the starting point for each unique
        branch in the tree.
    """
    nodes = {}
    nodes = build_nodes(lines)
    set_node_caller(nodes)
    set_node_info(symbols, nodes)
    #set_dispatch_tables(nodes, lines)

    #delete_invalid_nodes()
    #insert_vtables()
    
    #insert_stack_usage()
    
    #build_call_stacks(nodes)
    #visualise_dict()
 
    show_node_metrics(nodes)

    """ TODO implement long-term solution
    """
    with open( filename + '.json', 'w') as outfile:
        json.dump(nodes, outfile, indent=4)
    


def main():
    print("Stack Checker")
    filename = validate_input()
    
    symbols = {}
    build_symbol_table(symbols, filename)

    #build_symbols(filename)
    build_call_tree(symbols, filename)



if __name__ == "__main__":
    main()
