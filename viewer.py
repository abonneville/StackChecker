""" Simple dictionary viewer
    Inspired by: https://stackoverflow.com/questions/15023333/simple-tool-library-to-visualize-huge-python-dict
"""
import argparse
import json

import uuid
import tkinter as tk
from tkinter import ttk

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
        handle.close()


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


def tk_tree_view(data):
    """ Initialize how the call graph will be visually displayed
    """
    # Setup the root UI
    root = tk.Tk()
    root.title("Call Graph")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Setup the Frames
    tree_frame = ttk.Frame(root, padding="3")
    tree_frame.grid(row=0, column=0, sticky=tk.NSEW)

    # Setup the Tree
    style = ttk.Style()
    style.configure("mystyle.Treeview", highlightthickness=0, bd=0, font=('Calibri', 11)) # Modify the font of the body
    style.configure("mystyle.Treeview.Heading", font=('Calibri', 13,'bold')) # Modify the font of the headings
    #style.layout("mystyle.Treeview", [('mystyle.Treeview.treearea', {'sticky': 'nswe'})]) # Remove the borders

    tree = ttk.Treeview(tree_frame, selectmode='browse', style="mystyle.Treeview")
    
    tree['columns'] = ('1', '2')
    tree.column('#0', width=100, anchor=tk.W)
    tree.column('1', width=40, anchor=tk.CENTER)
    tree.column('2', width=40, anchor=tk.CENTER)

    tree.heading('#0', text='Function Name', anchor=tk.W)
    tree.heading('1', text='Level')
    tree.heading('2', text='Recursion')

    # attach a Vertical (y) scrollbar to the frame
    vsb = ttk.Scrollbar(tree_frame, orient='vertical')
    vsb.configure(command=tree.yview)
    vsb.pack(side='right', fill='y')
    tree.configure(yscrollcommand=vsb.set)


    # Fill tree with data
    j_tree(tree, '', data)
    tree.pack(fill=tk.BOTH, expand=1)

    # Limit windows minimum dimensions
    root.update_idletasks()
    root.minsize(2 * root.winfo_reqwidth(), root.winfo_reqheight())
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



