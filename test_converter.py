import unittest
import json
import converter as conv

def setUpModule():
    """ Run one-time before any testing is performed in this file
    """
    pass


def tearDownModule():
    """ Run one-time after all testing is completed in this file
    """
    pass


class RecursionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """ Run one-time before any testing is performed in this class
        """
        cls.filename = "test_recursion.json"
        cls.nodes = conv.Converter()
        cls.nodes.load(cls.filename)
        cls.nodes.to_call_list()
        cls.nodes.save(cls.filename)

    @classmethod
    def tearDownClass(cls):
        """ Run one-time after all testing is completed in this class
        """
        pass

    @classmethod
    def load(cls, filename):
        """ Gets the node list to be processed
        """
        with open(filename, 'r') as handle:
            dest = json.load(handle, object_hook=conv.jsonKeys2int)
        
        handle.close()
        return dest


    def test_root_node(self):
        # Verify root node detected
        self.assertFalse(False)
        result = self.nodes.call_graph.__len__()
        self.assertEqual(result, 4)
        self.assertTrue(1002 in self.nodes.call_graph)
        self.assertTrue(2002 in self.nodes.call_graph)
        self.assertTrue(3001 in self.nodes.call_graph)
        self.assertTrue(4001 in self.nodes.call_graph)

    def test_recursion(self):
        """ Load a golden reference for validating recursion was handled 
            correctly
        """
        expected = {}
        expected = self.load('test_recursion.expected.json')
        self.assertEqual(expected, self.nodes.call_graph)

unittest.main()