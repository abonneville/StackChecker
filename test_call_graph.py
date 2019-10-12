import unittest

import call_graph as cg

class SymbolTestCase(unittest.TestCase):

    def test_symbol_line_detect(self):
        result = cg.is_symbol_line("Startup.elf:     file format elf32-littlearm")
        self.assertEqual(result, False)

        result = cg.is_symbol_line("SYMBOL TABLE:")
        self.assertEqual(result, False)

        result = cg.is_symbol_line("")
        self.assertEqual(result, False)

        result = cg.is_symbol_line("08000000")
        self.assertEqual(result, False)

        result = cg.is_symbol_line("08000000 ")
        self.assertEqual(result, False)

        result = cg.is_symbol_line("080018a0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(result, True)

        result = cg.is_symbol_line("0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(result, True)


    def test_symbol_address(self):
        address = 0

        address = cg.get_symbol_address("4 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(address, 4)
        
        address = cg.get_symbol_address("080018a0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(address, 134224032)
        
    def test_symbol_name(self):

        name = cg.get_symbol_name("080018a0 l     F .text	0000008c p")
        self.assertEqual(name, "p")

        name = cg.get_symbol_name("080018a0 l     F .text	0000008c prvAddCurrentTaskToDelayedList")
        self.assertEqual(name, "prvAddCurrentTaskToDelayedList")

        name = cg.get_symbol_name("08002fd0 l     F .text	00000032 sensor::HTS221::impl::readByte(HTS221_Register) [clone .isra.0]")
        self.assertEqual(name, "sensor::HTS221::impl::readByte(HTS221_Register) [clone .isra.0]")


    def test_symbol_section(self):

        section = cg.get_symbol_section("080018a0 l     F .text	0000008c p")
        self.assertEqual(section, ".text")

        section = cg.get_symbol_section("080018a0 l     F .	0000008c p")
        self.assertEqual(section, ".")
        
        section = cg.get_symbol_section("080018a0 l     F 	0000008c p")
        self.assertEqual(section, "")


    def test_symbol_size(self):

        size = cg.get_symbol_size("080018a0 l     F .text	0000008c p")
        self.assertEqual(size, 140)

        size = cg.get_symbol_size("080018a0 l     F .text	8c p")
        self.assertEqual(size, 140)

        size = cg.get_symbol_size("080018a0 l     F .text	8 p")
        self.assertEqual(size, 8)

class LinkTestCase(unittest.TestCase):

    def test_node_start(self):

        result = cg.is_node_start("Startup.elf:     file format elf32-littlearm")
        self.assertEqual(result, False)

        result = cg.is_node_start("Disassembly of section .isr_vector:")
        self.assertEqual(result, False)

        result = cg.is_node_start("")
        self.assertEqual(result, False)

        result = cg.is_node_start("08000000:")
        self.assertEqual(result, False)

        result = cg.is_node_start("<g_pfnVectors>:")
        self.assertEqual(result, False)

        result = cg.is_node_start("08000000 <g_pfnVectors-0x123>:")
        self.assertEqual(result, False)

        result = cg.is_node_start("08000000 <g_pfnVectors+0x123>:")
        self.assertEqual(result, False)

        result = cg.is_node_start("08000000 g_pfnVectors:")
        self.assertEqual(result, True)

        result = cg.is_node_start("08000000 <g_pfnVectors>:")
        self.assertEqual(result, True)

    def test_get_node_address(self):

        address = cg.get_node_address("8 <g_pfnVectors>:")
        self.assertEqual(address, 8)

        address = cg.get_node_address("08000000 <g_pfnVectors>:")
        self.assertEqual(address, 134217728)

    def test_get_line_address(self):
        # Terminator for line containing start of node
        address = cg.get_line_address("8 <g_pfnVectors>:", ' ')
        self.assertEqual(address, 8)

        address = cg.get_line_address("08000000 <g_pfnVectors>:", ' ')
        self.assertEqual(address, 134217728)

        address = cg.get_line_address(" <g_pfnVectors>:", ' ')
        self.assertEqual(address, 0)

        # Alternate terminator for start of a line
        address = cg.get_line_address(" 8:	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 8)

        address = cg.get_line_address(" 80202f0:	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 134349552)

        address = cg.get_line_address(" :	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 0)

        address = cg.get_line_address(" 	0800074d 	stmdaeq	r0, {r0, r2, r3, r6, r8, r9, sl}", ':')
        self.assertEqual(address, 0)


    def test_is_node_branch(self):
        
        result = cg.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend>")
        self.assertEqual(result, True)

        result = cg.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend")
        self.assertEqual(result, False)

        result = cg.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 xQueueGenericSend>")
        self.assertEqual(result, False)

        result = cg.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend+0x123>")
        self.assertEqual(result, False)

        result = cg.is_node_branch(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend-0x123>")
        self.assertEqual(result, False)

    def test_get_branch_address(self):

        address = cg.get_branch_address(" 800ab5e:	f7f6 fa6f 	bl	8001040 <xQueueGenericSend>")
        self.assertEqual(address, 134221888)

        address = cg.get_branch_address(" 800ab5e:	f7f6 fa6f 	bl	8 <xQueueGenericSend>")
        self.assertEqual(address, 8)


unittest.main()