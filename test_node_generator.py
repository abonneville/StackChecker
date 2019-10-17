import unittest
from pathlib import Path

import json
import node_generator as ng
from converter import jsonKeys2int

class SymbolTestCase(unittest.TestCase):

    def test_symbol_line_detect(self):
        result = ng.is_symbol_line("Startup.elf:     file format elf32-littlearm")
        self.assertEqual(result, False)

        result = ng.is_symbol_line("SYMBOL TABLE:")
        self.assertEqual(result, False)

        result = ng.is_symbol_line("")
        self.assertEqual(result, False)

        result = ng.is_symbol_line("08000000")
        self.assertEqual(result, False)

        result = ng.is_symbol_line("08000000 ")
        self.assertEqual(result, False)

        result = ng.is_symbol_line("080018a0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(result, True)

        result = ng.is_symbol_line("0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(result, True)


    def test_symbol_address(self):
        address = 0

        address = ng.get_symbol_address("4 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(address, 4)
        
        address = ng.get_symbol_address("080018a0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(address, 134224032)
        
    def test_symbol_name(self):

        name = ng.get_symbol_name("080018a0 l     F .text	0000008c p")
        self.assertEqual(name, "p")

        name = ng.get_symbol_name("080018a0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(name, "prvAddCurrentTaskToDelayedList")

        name = ng.get_symbol_name("08002fd0 l     F .text	00000032 sensor::HTS221::impl::readByte(HTS221_Register) [clone .isra.0]")
        self.assertEqual(name, "sensor::HTS221::impl::readByte(HTS221_Register) [clone .isra.0]")


    def test_symbol_section(self):

        section = ng.get_symbol_section("080018a0 l     F .text	0000008c p")
        self.assertEqual(section, ".text")

        section = ng.get_symbol_section("080018a0 l     F .	0000008c p")
        self.assertEqual(section, ".")
        
        section = ng.get_symbol_section("080018a0 l     F 	0000008c p")
        self.assertEqual(section, "")


    def test_symbol_size(self):

        size = ng.get_symbol_size("080018a0 l     F .text	0000008c p")
        self.assertEqual(size, 140)

        size = ng.get_symbol_size("080018a0 l     F .text	8c p")
        self.assertEqual(size, 140)

        size = ng.get_symbol_size("080018a0 l     F .text	8 p")
        self.assertEqual(size, 8)

class LinkTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """ Run one-time before any testing is performed in this class
        """
        # Populate node list with known values, bypassing the *.elf conversion
        # process
        cls.nodes = ng.Node()
        infile = Path('test_node_generator.list.json')
        with open(infile, 'r') as handle:
            cls.nodes.nodes = json.load(handle, object_hook=jsonKeys2int)
        handle.close()

    @classmethod
    def tearDownClass(cls):
        """ Run one-time after all testing is completed in this class
        """
        pass

    def test_node_start(self):

        result = ng.is_node_start("Startup.elf:     file format elf32-littlearm")
        self.assertEqual(result, False)

        result = ng.is_node_start("Disassembly of section .isr_vector:")
        self.assertEqual(result, False)

        result = ng.is_node_start("")
        self.assertEqual(result, False)

        result = ng.is_node_start("08000000:")
        self.assertEqual(result, False)

        result = ng.is_node_start("<g_pfnVectors>:")
        self.assertEqual(result, False)

        result = ng.is_node_start("08000000 <g_pfnVectors-0x123>:")
        self.assertEqual(result, False)

        result = ng.is_node_start("08000000 <g_pfnVectors+0x123>:")
        self.assertEqual(result, False)

        result = ng.is_node_start("08000000 g_pfnVectors:")
        self.assertEqual(result, True)

        result = ng.is_node_start("08000000 <g_pfnVectors>:")
        self.assertEqual(result, True)

    def test_get_node_address(self):

        address = ng.get_node_address("8 <g_pfnVectors>:")
        self.assertEqual(address, 8)

        address = ng.get_node_address("08000000 <g_pfnVectors>:")
        self.assertEqual(address, 134217728)

    def test_get_line_address(self):
        # Terminator for line containing start of node
        address = ng.get_line_address("8 <g_pfnVectors>:", ' ')
        self.assertEqual(address, 8)

        address = ng.get_line_address("08000000 <g_pfnVectors>:", ' ')
        self.assertEqual(address, 134217728)

        address = ng.get_line_address(" <g_pfnVectors>:", ' ')
        self.assertEqual(address, 0)

        # Alternate terminator for start of a line
        address = ng.get_line_address(" 8:	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 8)

        address = ng.get_line_address(" 80202f0:	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 134349552)

        address = ng.get_line_address(" :	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 0)

        address = ng.get_line_address(" 	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 0)


    def test_is_node_branch(self):
        
        result = ng.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend>")
        self.assertEqual(result, True)

        result = ng.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend")
        self.assertEqual(result, False)

        result = ng.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 xQueueGenericSend>")
        self.assertEqual(result, False)

        result = ng.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend+0x123>")
        self.assertEqual(result, False)

        result = ng.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend-0x123>")
        self.assertEqual(result, False)

    def test_get_branch_address(self):

        address = ng.get_branch_address(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend>")
        self.assertEqual(address, 134221888)

        address = ng.get_branch_address(" 800ab5e:	f7f6 fa6f 	bl	8 <xQueueGenericSend>")
        self.assertEqual(address, 8)

    def test_get_pointer(self):
        pointer = ng.get_pointer(" 801fb2c:	f000 f888 	bl	801fc40 <_printf_i>")
        self.assertEqual(pointer, 0xf000)

        pointer = ng.get_pointer(" 801fb30:	e7ec      	b.n	801fb0c <_vfiprintf_r+0x1e4>")
        self.assertEqual(pointer, 0xe7ec)

        pointer = ng.get_pointer(" 801fb34:	08026394 	stmdaeq	r2, {r2, r4, r7, r8, r9, sp, lr}")
        self.assertEqual(pointer, 0x08026394)

        pointer = ng.get_pointer(" 801fb4c:	00000000 	andeq	r0, r0, r0")
        self.assertEqual(pointer, 0)

        pointer = ng.get_pointer(" 801fb50:	ffffffff 	stmdaeq	r1, {r0, r2, r8, fp, ip, sp, lr, pc}")
        self.assertEqual(pointer, 0xffffffff)

        pointer = ng.get_pointer(" 801fb50:	hello 	stmdaeq	r1, {r0, r2, r8, fp, ip, sp, lr, pc}")
        self.assertEqual(pointer, -1)

    def test_link_to_function(self):
        """ This test will utilize a known node list to validate unit under
            test.

            Note: the unit under test (UUT) assumes a valid parent was
            established prior to invoking this UUT. This UUT only validates the
            child request.
        """
        # Valid parent and child link request
        parent = 134251848 # main()
        child = 134231972 # HAL_DMA_Abort_IT(), arbitrator selection
        self.assertEqual(0, len(self.nodes.nodes[parent]['branch']) )
        self.nodes.link_to_function(parent, child)
        self.assertEqual(1, len(self.nodes.nodes[parent]['branch']) )
        self.assertTrue( child in self.nodes.nodes[parent]['branch'] )

        # Verify redundant request to link is ignored
        self.nodes.link_to_function(parent, child)
        self.assertEqual(1, len(self.nodes.nodes[parent]['branch']) )
        self.assertTrue( child in self.nodes.nodes[parent]['branch'] )

        # Valid parent, invalid child link request
        child = 268437784 # msgQueue, a variable
        self.nodes.link_to_function(parent, child)
        self.assertEqual(1, len(self.nodes.nodes[parent]['branch']) )
        self.assertTrue( not child in self.nodes.nodes[parent]['branch'] )

        # Valid parent, invalid child link request
        child = 0 # invald node, non-existent
        self.nodes.link_to_function(parent, child)
        self.assertEqual(1, len(self.nodes.nodes[parent]['branch']) )
        self.assertTrue( not child in self.nodes.nodes[parent]['branch'] )


unittest.main()