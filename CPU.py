import struct

class cpu:
	def __init__(self):
		self._memory = [] 	# Memory
		self.PC = 0       	# program counter
		self.SP = 0xF000  	# stack pointer
		self.A = 0			# Accumulator
		self.B = 0
		self.C = 0
		self.D = 0
		self.E = 0
		self.H = 0
		self.L = 0
		self.BC = 0			# BC Register
		self.DE = 0			# DE Register
		self.HL = 0
		self.SIGN = False 
		self.ZERO = False
		self.HALFCARRY = False
		self.PARITY = False
		self.CARRY = False
		self.INTERRUPT = False
		self.current_inst = 0 # current instruction
		
		self.interrupt_alternate = False
		self.count = 0
		self.cycles = 0
		self.mappingTable = [0] * 0x100
		
	
	def loadROM(self, path):
		rom = open(path, 'rb')
		image = rom.read()
		i = 0
		maxlines = 20
		while i < len(image):
			opcode = image[i]
			str = '0x%02X' % opcode
			print(str)
			self._memory.append(opcode)
			#if i > maxlines:
			#	break
			#else:
			i += 1
		rom.close()
		self._memory += [0] * (65536 - len(self._memory)) # ROM + RAM(work RAM and video RAM) = 16384 0x3fff
	
	# Reset
	def reset(self):
		self.PC = 0
		self.A = 0
		self.setBC(0)
		self.setHL(0)
		self.SIGN = False 
		self.ZERO = False
		self.HALFCARRY = False
		self.PARITY = False
		self.CARRY = False
		self.INTERRUPT = False
	
	def Run(self): # CPU Run
		for i in range(16667):
			self.execINST()
			
	def runCycles(self, cycles):
		for i in range(cycles):
			self.execINST()
		return self.PC
		
	def execINST(self):
		print('PC: ', self.PC)
		self.current_inst = self.FetchRomNext1Byte()
		if not self.mappingTable[self.current_inst] == None:
			str = '0x%02X' % self.current_inst
			print('current_inst: ', str)
			self.mappingTable[self.current_inst]()
		else:
			print ("opCODE ERROR: " + str(self.cuttent_inst))
		self.count += 1
		
		# Check interrupt
		if self.cycles >= 16667:	# Check Interrupt
			self.cycles -= 16667
			if self.INTERRUPT:
				if self.interrupt_alternate == True:
					self.callInterrupt(0x08)
				else:
					self.callInterrupt(0x10)
				self.interrupt_alternate = not self.interrupt_alternate
				
	def callInterrupt(self, address):
		self.stackPush(self.PC)
		self.PC = address
	
	
	def INST_NOP(self):
		# NOP
		self.cycles += 4
		
	def INST_JMP(self): # JMP
		condition = True
		data_16 = self.FetchRomNext2Bytes()
		self.cycles += 10
		
		if 0xC3 == self.current_inst: # JMP
			self.PC = data_16
			return
		elif self.current_inst == 0xC2: # JNZ
			condition = not self.ZERO   # if not z
		elif self.current_inst == 0xCA: # JZ
			condition = self.ZERO
		elif self.current_inst == 0xD2: # JNC
			condition = not self.CARRY  # if not c
		elif self.current_inst == 0xDA: # JC
			condition = self.CARRY	    # if C
		elif self.current_inst == 0xF2: # JP
			condition = not self.SIGN   # if P
		elif self.current_inst == 0xFA: # JM
			condition = self.SIGN
			
		if condition:
			self.PC = data_16
			self.cycles += 5

	# LDA load A from memory
	def INST_LDA(self): 
		if self.current_inst == 0x0A:
			source = self.BC
		elif self.current_inst == 0x1A:
			source = self.DE
		elif self.current_inst == 0x3A:
			source = self.FetchRomNext2Bytes()
			self.cycles += 6
		else:
			source = 0
			print ('LDA problem')
			exit(1)
			
		self.A = self.readByte(source)
		self.cycles += 7
		
	# PUSH
	def INST_PUSH(self):
		if self.current_inst == 0xC5:
			value = self.BC
		elif self.current_inst == 0xD5:
			value = self.DE
		elif self.current_inst == 0xE5:
			value = self.HL
		elif self.current_inst == 0xF5:
			value = (self.A << 8) + 0x02
			value += 0x80 if self.SIGN else 0
			value += 0x40 if self.ZERO else 0
			value += 0x10 if self.HALFCARRY else 0
			value += 0x04 if self.PARITY else 0
			value += 0x04 if self.PARITY else 0
		else:
			value = 0
			print ("Instruction Push Error: " + str(self.current_inst))
			exit(1)
	
	# RRC Rotate A right
	def INST_RRC(self):
		self.CARRY = True if (self.A & 0x01) == 1 else False
		self.A = ((self.A >> 1) & 0xFF) + ((self.A << 7) & 0xFF)
		self.cycles += 4
	
	# RAL Rotate A left through carry
	def INST_RAL(self):
		temp = self.A
		self.A = (self.A << 1) & 0xFF
		self.A += 1 if self.CARRY else 0
		self.CARRY = True if (temp & 0x80) > 0 else False
		self.cycles += 4
		
	
	
	# STA Store A to memory
	def INST_STA(self):
		if self.current_inst == 0x02:
			self.writeByte(self.BC, self.A)
		elif self.current_inst == 0x12:
			self.writeByte(self.DE, self.A)
		elif self.current_inst == 0x32:
			self.writeByte(self.FetchRomNext2Bytes(), self.A)
			self.cycles += 6
		else:
			print('no matching rules for STA INST')
			exit(1)
		self.cycles += 7
	
	
	def INST_toImplement(self):
		str = '0x%02X' % self.current_inst
		print(str, ' is not implemented')
		#exit(1)
	
	# C<-1
	def INST_STC(self):
		self.CARRY = True
		self.cycles += 4
	
	#Move register to register
	def INST_MOVHL(self):
		if self.current_inst == 0x77: 			# MOV M, A
			self.writeByte(self.HL, self.A)		
		elif self.current_inst == 0x70:			# MOV M, B
			self.writeByte(self.HL, self.B)
		elif self.current_inst == 0x71:			# MOV M, C
			self.writeByte(self.HL, self.C)
		elif self.current_inst == 0x72:			# MOV M, D
			self.writeByte(self.HL, self.D)
		elif self.current_inst == 0x73:			# MOV M, E
			self.writeByte(self.HL, self.E)
		elif self.current_inst == 0x74:			# MOV M, H
			self.writeByte(self.HL, self.H)
		elif self.current_inst == 0x75:			# MOV M, L
			self.writeByte(self.HL, self.L)
			
		self.cycles += 7
		
	
	
	# Move register to register
	def INST_MOV(self):
		if self.current_inst == 0x7F:
			self.A = self.A
		elif self.current_inst == 0x78:
			self.A = self.B
		elif self.current_inst == 0x79:
			self.A = self.C
		elif self.current_inst == 0x7A:
			self.A = self.D
		elif self.current_inst == 0x7B:
			self.A = self.E
		elif self.current_inst == 0x7C:
			self.A = self.H
		elif self.current_inst == 0x7D:
			self.A = self.L
		elif self.current_inst == 0x7E:
			self.A = self.readByte(self.HL)
			self.cycles += 2
			
		elif self.current_inst == 0x47:
			self.setB(self.A)
		elif self.current_inst == 0x40:
			self.B = self.B
		elif self.current_inst == 0x41:
			self.setB(self.C)
		elif self.current_inst == 0x42:
			self.setB(self.D)
		elif self.current_inst == 0x43:
			self.setB(self.E)
		elif self.current_inst == 0x44:
			self.setB(self.H)
		elif self.current_inst == 0x45:
			self.setB(self.L)
		elif self.current_inst == 0x46:
			self.setB(self.readByte(self.HL))
			self.cycles += 2
			
		elif self.current_inst == 0x4F:
			self.setC(self.A)
		elif self.current_inst == 0x48:
			self.setC(self.B)
		elif self.current_inst == 0x49:
			self.C = self.C
		elif self.current_inst == 0x4A:
			self.setC(self.D)
		elif self.current_inst == 0x4B:
			self.setC(self.E)
		elif self.current_inst == 0x4C:
			self.setC(self.H)
		elif self.current_inst == 0x4D:
			self.setC(self.L)
		elif self.current_inst == 0x4E:
			self.setC(self.readByte(self.HL))
			self.cycles += 2
			
		elif self.current_inst == 0x57:
			self.setD(self.A)
		elif self.current_inst == 0x50:
			self.setD(self.B)
		elif self.current_inst == 0x51:
			self.setD(self.C)
		elif self.current_inst == 0x52:
			self.D = self.D
		elif self.current_inst == 0x53:
			self.setD(self.E)
		elif self.current_inst == 0x54:
			self.setD(self.H)
		elif self.current_inst == 0x55:
			self.setD(self.L)
		elif self.current_inst == 0x56:
			self.setD(self.readByte(self.HL))
			self.cycles += 2
			
		elif self.current_inst == 0x5F:
			self.setE(self.A)
		elif self.current_inst == 0x58:
			self.setE(self.B)
		elif self.current_inst == 0x59:
			self.setE(self.C)
		elif self.current_inst == 0x5A:
			self.setE(self.D)
		elif self.current_inst == 0x5B:
			self.E = self.E
		elif self.current_inst == 0x5C:
			self.setE(self.H)
		elif self.current_inst == 0x5D:
			self.setE(self.L)
		elif self.current_inst == 0x5E:
			self.setE(self.readByte(self.HL))
			self.cycles += 2
		
		elif self.current_inst == 0x67:
			self.setH(self.A)
		elif self.current_inst == 0x60:
			self.setH(self.B)
		elif self.current_inst == 0x61:
			self.setH(self.C)
		elif self.current_inst == 0x62:
			self.setH(self.D)
		elif self.current_inst == 0x63:
			self.setH(self.E)
		elif self.current_inst == 0x64:
			self.H = self.H
		elif self.current_inst == 0x65:
			self.setH(self.L)
		elif self.current_inst == 0x66:
			self.setE(self.readByte(self.HL))
			self.cycles += 2
			
		elif self.current_inst == 0x6F:
			self.setL(self.A)
		elif self.current_inst == 0x68:
			self.setL(self.B)
		elif self.current_inst == 0x69:
			self.setL(self.C)
		elif self.current_inst == 0x6A:
			self.setL(self.D)
		elif self.current_inst == 0x6B:
			self.setL(self.E)
		elif self.current_inst == 0x6D:
			self.L = self.L
		elif self.current_inst == 0x6C:
			self.setL(self.H)
		elif self.current_inst == 0x66:
			self.setL(self.readByte(self.HL))
			self.cycles += 2
		else:
			print('NO matching rules for MOV INST')
			exit(1)
		
		self.cycles += 5
		
	# Increment register pair
	def INST_INX(self):
		if self.current_inst == 0x03:
			self.setBC(self.BC + 1)
		elif self.current_inst == 0x13:
			self.setDE(self.DE + 1)
		elif self.current_inst == 0x23:
			self.setHL(self.HL + 1)
		elif self.current_inst == 0x33:
			self.SP = (self.SP + 1) & 0xFF
		
		self.cycles += 6
	
	# DAD_DE Add register pair to HL (16 bit add)
	def INST_DAD_DE(self):
		self.addHL(self.DE)
		self.cycles += 11
		
	
	# Increment register
	def INST_INR(self):
		if self.current_inst == 0x3C:
			self.A = self.Inc(self.A)
		elif self.current_inst == 0x04:
			self.setB(self.Inc(self.B))
		elif self.current_inst == 0x0C:
			self.setC(self.Inc(self.C))
		elif self.current_inst == 0x14:
			self.setD(self.Inc(self.D))
		elif self.current_inst == 0x1C:
			self.setE(self.Inc(self.E))
		elif self.current_inst == 0x24:
			self.setH(self.Inc(self.H))
		elif self.current_inst == 0x2C:
			self.setL(self.Inc(self.L))
		elif self.current_inst == 0x34:
			self.writeByte(self.HL, self.Inc(self.readByte(self.HL)))
			self.cycles += 5
		self.cycles += 5
	
	# Decrement register
	def INST_DEC(self):
		if self.current_inst == 0x3D:
			self.A = self.Dec(self.A)
		elif self.current_inst == 0x05:
			self.setB(self.Dec(self.B))
		elif self.current_inst == 0x0D:
			self.setC(self.Dec(self.C))
		elif self.current_inst == 0x15:
			self.setD(self.Dec(self.D))
		elif self.current_inst == 0x1D:
			self.setE(self.Dec(self.E))
		elif self.current_inst == 0x25:
			self.setH(self.Dec(self.H))
		elif self.current_inst == 0x2D:
			self.setL(self.Dec(self.L))
		elif self.current_inst == 0x35:
			self.writeByte(self.HL, self.Dec(self.readByte(self.HL)))
			self.cycles += 5
		else:
			print('DEC ERROR')
			exit(1)
		self.cycles += 5
			
	
	# AND register with A, B, C, D, E, H, L	
	def INST_AND(self):
		if self.current_inst == 0xA7:
			self.And(self.A)
		elif self.current_inst == 0xA0:
			self.And(self.B)
		elif self.current_inst == 0xA1:
			self.And(self.C)
		elif self.current_inst == 0xA2:
			self.And(self.D)
		elif self.current_inst == 0xA3:
			self.And(self.E)
		elif self.current_inst == 0xA4:
			self.And(self.H)
		elif self.current_inst == 0xA5:
			self.And(self.L)
		elif self.current_inst == 0xA6:
			self.And(self.readByte(self.HL))
			self.cycles += 3
		elif self.current_inst == 0xE6:
			self.And(self.FetchRomNext1Byte())
			self.cycles += 3
			
		self.cycles += 4
		
		
		
		
	
	# Add register to A, B, C, D, E, H, L
	def INST_ADD(self):
		if self.current_inst == 0x87:
			self.Add(self.A)
		elif self.current_inst == 0x80:
			self.Add(self.B)
		elif self.current_inst == 0x81:
			self.Add(self.C)
		elif self.current_inst == 0x82:
			self.Add(self.D)
		elif self.current_inst == 0x83:
			self.Add(self.E)
		elif self.current_inst == 0x84:
			self.Add(self.H)
		elif self.current_inst == 0x85:
			self.Add(self.L)
		elif self.current_inst == 0x86:
			self.Add(self.readByte(self.HL))
			self.cycles += 3
		elif self.current_inst == 0xC6:
			self.Add(self.FetchRomNext1Byte())
			self.cycles += 3
			
		self.cycles += 4
		
	
	# Add register to A, B, C, D, E, H, L with carry
	def INST_ADC(self):
		carry = 1 if self.CARRY else 0
		if self.current_inst == 0x8F:
			self.Add(self.A, carry)
		elif self.current_inst == 0x88:
			self.Add(self.B, carry)
		elif self.current_inst == 0x89:
			self.Add(self.C, carry)
		elif self.current_inst == 0x8A:
			self.Add(self.D, carry)
		elif self.current_inst == 0x8B:
			self.Add(self.E, carry)
		elif self.current_inst == 0x8C:
			self.Add(self.H, carry)
		elif self.current_inst == 0x8D:
			self.Add(self.L, carry)
		elif self.current_inst == 0x8E:
			self.Add(self.readByte(self.HL), carry)
			self.cycles += 3
		elif self.current_inst == 0xCE:
			self.Add(self.FetchRomNext1Byte(), carry)
			self.cycles += 3
			
		self.cycles += 4
		
		
		
	
	def INST_LXI_BC(self):  # B <- byte 3, C <- byte 2
		self.setBC(self.FetchRomNext2Bytes())
		self.cycles += 10
	
	def INST_LXI_DE(self):  # D <- byte 3, E <- byte 2
		self.setDE(self.FetchRomNext2Bytes())
		self.cycles += 10
	
	def INST_LXI_HL(self):  # H <- byte 3, L <- byte 2
		self.setHL(self.FetchRomNext2Bytes())
		self.cycles += 10
	
	def INST_LXI_SP(self):
		self.SP = self.FetchRomNext2Bytes()
		self.cycles += 10
		
	def INST_MVI_A(self): # A <- byte2
		self.setA(self.FetchRomNext1Byte())
		self.cycles += 7
		
	def INST_MVI_B(self): # B <- byte2
		self.setB(self.FetchRomNext1Byte())
		self.cycles += 7
	
	def INST_MVI_C(self): # C <- byte2
		self.setC(self.FetchRomNext1Byte())
		self.cycles += 7
		
	def INST_MVI_D(self): # D <- byte2
		self.setD(self.FetchRomNext1Byte())
		self.cycles += 7
		
	def INST_MVI_E(self): # E <- byte2
		self.setE(self.FetchRomNext1Byte())
		self.cycles += 7
	
	def INST_MVI_H(self):
		self.setH(self.FetchRomNext1Byte())
		self.cycles += 7
		
	def INST_MVI_L(self): # L <- byte2
		self.setL(self.FetchRomNext1Byte())
		self.cycles += 7
	
	def INST_MVI_M(self): 
		self.writeByte(self.HL, self.FetchRomNext1Byte())
		self.cycles += 10
		
	def INST_MVI_B(self): # B <- byte2
		self.setB(self.FetchRomNext1Byte())
		self.cycles += 7
		
	# Unconditional subroutine call
	def INST_CALL(self):
		condition = True
		data_16 = self.FetchRomNext2Bytes()
		self.cycles += 11
		
		if self.current_inst == 0xCD: # CALL adr	3		(SP-1)<-PC.hi;(SP-2)<-PC.lo;SP<-SP+2;PC=adr
			self.stackPush(self.PC)
			self.PC = data_16
			self.cycles += 6
			return
		elif self.current_inst == 0xC4: # if NZ, CALL adr
			condition = not self.ZERO
		elif self.current_inst == 0xCC:
			condition = self.ZERO
		elif self.current_inst == 0xD4:
			condition = not self.CARRY
		elif self.current_inst == 0xDC:
			condition = self.CARRY
			
		if condition:
			self.stackPush(self.PC)
			self.PC = data_16
			self.cycles += 7
		
	# Unconditional return from subroutine
	def INST_RET(self):
		condition = True
		self.cycles += 5
		
		if self.current_inst == 0xC9:
			self.PC = self.stackPop()
			self.cycles += 5
			return
		elif self.current_inst == 0xC0:
			condition = not self.ZERO
		elif self.current_inst == 0xC8:
			condition = self.ZERO
		elif self.current_inst == 0xD0:
			condition = not self.CARRY
		elif self.current_inst == 0xD8:
			condition = self.CARRY
			
		if condition:
			self.PC = self.stackPop()
			self.cycles += 6
			
	# Compare register with A, B, C, D, E, H, L	
	def INST_CMP(self):
		if self.current_inst == 0xBF:
			value = self.A
		elif self.current_inst == 0xB8:
			value = self.B
		elif self.current_inst == 0xB9:
			value = self.C
		elif self.current_inst == 0xBA:
			value = self.D
		elif self.current_inst == 0xBB:
			value = self.E
		elif self.current_inst == 0xBC:
			value = self.H
		elif self.current_inst == 0xBD:
			value = self.L
		elif self.current_inst == 0xBE:
			value = self.readByte(self.HL)
			self.cycles += 3
		elif self.current_inst == 0xFE:
			value = self.FetchRomNext1Byte()
			self.cycles += 3
		else:
			value = 0
			print ('CMP error')
		self.CmpSub(value)
		
		self.cycles += 4
		
	
	# XCHG Exchange DE and HL content
	def INST_XCHG(self):
		temp = self.HL
		self.setHL(self.DE)
		self.setDE(temp)
		self.cycles += 4
		
	
	
	# INP Read input port into A
	def INST_INP(self):
		port = self.FetchRomNext1Byte()
		self.A = self.io.InPutPort(port)
		if self.A > 255:
			print ('Input Error')
			exit(1)
		self.cycles += 10
	
	# DAA Decimal Adjust accumulator
	def INST_DAA(self):
		if (self.A & 0x0F) > 9 or self.HALFCARRY:
			self.A += 0x06
			self.HALFCARRY = True
			
		if (self.A > 0x9F) or self.CARRY:
			self.A += 0x60
			self.CARRY = True
			
		self.ZERO = True if self.A == 0 else False
		self.SIGN = True if (self.A & 0x80) > 0 else False
		self.PARITY = True if self.A % 2 == 0 else False
		self.cycles += 4
		
	
	def INST_HLT(self):
		print ('HLT')
		exit(0)
	
	def setB(self, data):
		self.B = data & 0xFF
		self.BC = (self.B << 8) + self.C
		
	def setC(self, data):
		self.C = data & 0xFF
		self.BC = (self.B << 8) + self.C
		
	def setH(self, data):
		self.H = data & 0xFF
		self.HL = (self.H << 8) + self.L
		

	def setBC(self, data):
		self.BC = data & 0xFFFF
		self.B = self.BC >> 8
		self.C = self.BC & 0xFF
		
	def setDE(self, data):
		self.DE = data & 0xFFFF
		self.D = self.DE >> 8
		self.E = self.DE & 0xFF
		
	def setHL(self, data):
		self.HL = data & 0xFFFF
		self.H = self.HL >> 8
		self.L = self.HL & 0xFF
		
	def addHL(self, data):
		value = self.HL + data
		self.setHL(value)
		if value > 0xFFFF:
			self.CARRY = True
	
	# i++
	def Inc(self, data):
		value = (data + 1) & 0xFF
		self.ZERO = True if value == 0 else False
		self.SIGN = True if (value & 0x80) > 0 else False
		self.HALFCARRY = True if value % 2 == 0 else False
		self.PARITY = True if value % 2 == 0 else False
		return value
		
	# i--
	def Dec(self, data):
		value = (data + 1) & 0xFF
		self.HALFCARRY = True if (data & 0x0F) == 0 else False
		self.SIGN = True if (value & 0x80) > 0 else False
		self.ZERO = True if value == 0 else False
		self.PARITY = True if value % 2 == 0 else False
		return value
		
	
	def FetchRomNext1Byte(self):  # read next 8bit
		data = self._memory[self.PC]
		self.PC += 1
		return data
		
	def FetchRomNext2Bytes(self):  # read next 16bit
		data = (self._memory[self.PC + 1] << 8) + self._memory[self.PC]  # notice the endian
		self.PC += 2
		return data
		
	def CmpSub(self, in_value):
		value = self.A - in_value
		self.CARRY = True if value >= 255 or value < 0 else False
		self.HALFCARRY = True if ((self.A ^ value) ^ in_value) & 0x10 > 0 else False
		self.ZERO = True if value & 0xFF== 0 else False
		self.SIGN = True if (value & 0x80) > 0 else False
		self.PARITY = True if value%2==0 else False
		
	
	def stackPush(self, data):
		if data > 0xFFFF:
			print ('Push Error data:', data)
			print ('Count:', self.count)
			exit(1)
		self.SP -= 2
		self.write2Byte(self.SP, data)
		
	def stackPop(self):
		address = self.read2Bytes(self.SP)
		self.SP += 2
		return address
	
	def readByte(self, address):
		print('ReadByte:', address)
		if self._memory[address] > 0xFF:
			print ('readByte Error')
			exit(1)
		return self._memory[address]
		
	def read2Bytes(self, address):
		return (self._memory[address + 1] << 8) + self._memory[address]
	
	def writeByte(self, address, data):
		self._memory[address] = data & 0xFF
		
	def write2Byte(self, address, data):
		self._memory[address + 1] = data >> 8
		self._memory[address] = data & 0xFF
  
  
	
	def InitMap(self):
		print ('InitMap start')
		for i in range(len(self._memory)):
			opcode = self._memory[i]
			#print('InitMap ', opcode)
			if opcode == 0x00:
				self.mappingTable[self._memory[i]] = self.INST_NOP
				#print ('NOP', opcode)
			elif opcode == 0x01:
				self.mappingTable[self._memory[i]] = self.INST_LXI_BC
				print ('LXI_BC')
			elif opcode == 0x03:
				self.mappingTable[self._memory[i]] = self.INST_INX
				print ('INX')
			elif opcode == 0x05:
				self.mappingTable[self._memory[i]] = self.INST_DEC
				print ('DEC')
			elif opcode == 0x06:
				self.mappingTable[self._memory[i]] = self.INST_MVI_B
				print ('LDA')
			elif opcode == 0x0A:
				self.mappingTable[self._memory[i]] = self.INST_LDA
				print ('LDA')
			elif opcode == 0x0E:
				self.mappingTable[self._memory[i]] = self.INST_MVI_C
				print ('MVI_C')
			elif opcode == 0x0F:
				self.mappingTable[self._memory[i]] = self.INST_RRC
				print ('RRC')
			elif opcode == 0x11:
				self.mappingTable[self._memory[i]] = self.INST_LXI_DE
				print ('LXI_DE')
			elif opcode == 0x13:
				self.mappingTable[self._memory[i]] = self.INST_INX
				print ('INX')
			elif opcode == 0x17:
				self.mappingTable[self._memory[i]] = self.INST_RAL
				print ('RAL')
			elif opcode == 0x18:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x19:
				self.mappingTable[self._memory[i]] = self.INST_DAD_DE
				print ('DAD_DE')
			elif opcode == 0x1A:
				self.mappingTable[self._memory[i]] = self.INST_LDA
				print ('LDA')
			elif opcode == 0x20:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x21:
				self.mappingTable[self._memory[i]] = self.INST_LXI_HL
				print ('LXI_HL')
			elif opcode == 0x23:
				self.mappingTable[self._memory[i]] = self.INST_INX
				print ('INX')
			elif opcode == 0x26:
				self.mappingTable[self._memory[i]] = self.INST_MVI_H
				print ('MVI_H')
			elif opcode == 0x27:
				self.mappingTable[self._memory[i]] = self.INST_DAA
				print ('DAA')
			elif opcode == 0x6F:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x7C:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x80:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x81:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x82:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x83:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x84:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x85:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x86:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0x87:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0xC0:
				self.mappingTable[self._memory[i]] = self.INST_RET
				print ('RET')
			elif opcode == 0xC2:
				self.mappingTable[self._memory[i]] = self.INST_JMP
				print ('JMP')
			elif opcode == 0xC3:
				self.mappingTable[self._memory[i]] = self.INST_JMP
				print ('JMP')
			elif opcode == 0xC8:
				self.mappingTable[self._memory[i]] = self.INST_RET
				print ('RET')
			elif opcode == 0xC9:
				self.mappingTable[self._memory[i]] = self.INST_RET
				print ('RET')
			elif opcode == 0x3A:
				self.mappingTable[self._memory[i]] = self.INST_LDA
				print ('LDA')
			elif opcode == 0x30:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x31:
				self.mappingTable[self._memory[i]] = self.INST_LXI_SP
				print ('LXI_SP')
			elif opcode == 0x32:
				self.mappingTable[self._memory[i]] = self.INST_STA
				print ('STA')
			elif opcode == 0x33:
				self.mappingTable[self._memory[i]] = self.INST_INX
				print ('INX')
			elif opcode == 0x34:
				self.mappingTable[self._memory[i]] = self.INST_INR
				print ('INR')
			elif opcode == 0x35:
				self.mappingTable[self._memory[i]] = self.INST_DEC
				print ('DEC')
			elif opcode == 0x36:
				self.mappingTable[self._memory[i]] = self.INST_MVI_M
				print ('MVI_M')
			elif opcode == 0x37:
				self.mappingTable[self._memory[i]] = self.INST_STC
				print ('STC')
			elif opcode == 0x38:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x3E:
				self.mappingTable[self._memory[i]] = self.INST_MVI_A
				print ('MVI_A')
			elif opcode == 0x41:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x42:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x43:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x44:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x44:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x45:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x46:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x47:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x48:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x49:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x4A:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x4B:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x4C:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x4D:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x4E:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x4F:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x50:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x51:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x52:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x53:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x54:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x55:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x56:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x57:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x58:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x59:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x5A:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x5B:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x5C:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x5D:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x5E:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x5F:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x60:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x61:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x62:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x63:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x64:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x65:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x66:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x67:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x68:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x69:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x6A:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x6B:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x6C:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x6D:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x6E:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x6F:
				self.mappingTable[self._memory[i]] = self.INST_MOV
				print ('MOV')
			elif opcode == 0x70:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x71:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x72:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x73:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x74:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x75:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x76:
				self.mappingTable[self._memory[i]] = self.INST_HLT
				print ('HLT')
			elif opcode == 0x77:
				self.mappingTable[self._memory[i]] = self.INST_MOVHL
				print ('MOVHL')
			elif opcode == 0x8C:
				self.mappingTable[self._memory[i]] = self.INST_ADC
				print ('ADC')
			elif opcode == 0x98:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x99:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x9A:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x9B:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x9C:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x9D:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x9E:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0x9F:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0xA0:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA1:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA2:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA3:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA4:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA5:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA6:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xA7:
				self.mappingTable[self._memory[i]] = self.INST_AND
				print ('AND')
			elif opcode == 0xC5:
				self.mappingTable[self._memory[i]] = self.INST_PUSH
				print ('PUSH')
			elif opcode == 0xC6:
				self.mappingTable[self._memory[i]] = self.INST_ADD
				print ('ADD')
			elif opcode == 0xCA:
				self.mappingTable[self._memory[i]] = self.INST_JMP
				print ('JMP')
			elif opcode == 0xCD:
				self.mappingTable[self._memory[i]] = self.INST_CALL
				print ('CALL')
			elif opcode == 0xD4:
				self.mappingTable[self._memory[i]] = self.INST_CALL
				print ('CALL')
			elif opcode == 0xD5:
				self.mappingTable[self._memory[i]] = self.INST_PUSH
				print ('PUSH')
			elif opcode == 0xDB:
				self.mappingTable[self._memory[i]] = self.INST_INP
				print ('INP')
			elif opcode == 0xDA:
				self.mappingTable[self._memory[i]] = self.INST_JMP
				print ('JMP')
			elif opcode == 0xE5:
				self.mappingTable[self._memory[i]] = self.INST_PUSH
				print ('PUSH')
			elif opcode == 0xEA:
				self.mappingTable[self._memory[i]] = self.INST_toImplement
				print ('toImplement')
			elif opcode == 0xEB:
				self.mappingTable[self._memory[i]] = self.INST_XCHG
				print ('XCHG')
			elif opcode == 0xF5:
				self.mappingTable[self._memory[i]] = self.INST_PUSH
				print ('PUSH')
			elif opcode == 0xFE:
				self.mappingTable[self._memory[i]] = self.INST_CMP
				print ('CMP')
			else:
				str = '0x%02X' % opcode
				print ('Function not coded', str)
				exit(1)
	
	def information(self):
		print ('PC:%x' % self.PC, self.PC)
		print ('SP:%x' % self.SP, self.SP)
		for i in range(20):
			print ('%x: %s' % (self.PC+i, self._memory[self.PC+i]))
			
		

		
