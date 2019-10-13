""" Simple dictionary viewer
    Inspired by: https://stackoverflow.com/questions/15023333/simple-tool-library-to-visualize-huge-python-dict
"""
import argparse
import json

import uuid
import tkinter as tk
from tkinter import ttk

import test

class Viewer:
    """ Displays a call graph from a nested dictionary
    """
    def __init__(self, filename):
        self.filename = filename
        self.call_stacks = {}

    def load(self):
        """ Get call graph
        """
        with open(self.filename, 'r') as handle:
            self.call_stacks = json.load(handle)


    def show(self):
        """ Display call graph to user
        """
        tk_tree_view(self.call_stacks)


def j_tree(tree, parent, dic):
    """ Build the nested dictionary elements into a tree format
    """
    for key, field in dic.items():
        uid = uuid.uuid4()
        if isinstance(dic[key], dict):
            tree.insert(parent, 'end', uid, text=field['name'], value=(field['level'], field['recursion']))
            j_tree(tree, uid, dic[key])
        """
        elif isinstance(dic[key], tuple):
            tree.insert(parent, 'end', uid, text=str(key) + '()')
            j_tree(tree, uid,
                   dict([(i, x) for i, x in enumerate(dic[key])]))
        elif isinstance(dic[key], list):
            tree.insert(parent, 'end', uid, text=str(key) + '[]')
            j_tree(tree, uid,
                   dict([(i, x) for i, x in enumerate(dic[key])]))
        else:
            value = dic[key]
            if isinstance(value, str):
                value = value.replace(' ', '_')
            tree.insert(parent, 'end', uid, text=key, value=value)
        """


def tk_tree_view(data):
    """ Initialize how the call graph will be visually displayed
    """
    # Setup the root UI
    root = tk.Tk()
    root.title("tk_tree_view")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Setup the Frames
    tree_frame = ttk.Frame(root, padding="3")
    tree_frame.grid(row=0, column=0, sticky=tk.NSEW)

    # Setup the Tree
    tree = ttk.Treeview(tree_frame, columns=('Level', 'Recursion'))
    tree.column('Recursion', width=50, anchor='center')
    tree.heading('Recursion', text='Recursion')

    tree.column('Level', width=50, anchor='center')
    tree.heading('Level', text='Level')

    j_tree(tree, '', data)
    tree.pack(fill=tk.BOTH, expand=1)

    # Limit windows minimum dimensions
    root.update_idletasks()
    root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())
    root.mainloop()

def validate_input():
    """ Assess command line arguments
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--infile', 
                        help="input file, JSON format", metavar="FILE",
                        type=argparse.FileType('r', encoding='UTF-8'), 
                        required=True)

    args = parser.parse_args()
    args.infile.close()

    return args.infile.name

def main():
    print("Viewer")
    filename = validate_input()

    viewer = Viewer(filename)
    viewer.load()
    viewer.show()


if __name__ == "__main__":
    main()



