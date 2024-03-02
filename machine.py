#!/usr/bin/python3
import logging
import sys

from isa import *


logger = logging.getLogger("machine_logger")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class ALU:
    def __init__(self):
        self.left = 0
        self.right = 0
        self.N = 0
        self.Z = 1
        self.C = 0

    def set_flags(self, res):
        self.N = 1 if res < 0 else 0
        self.Z = 1 if res == 0 else 0

    def invert_string(self, s):
        return "".join(["1" if c == "0" else "0" for c in s])

    def to_unsigned(self, a):
        return int(self.invert_string(bin(abs(a))[2:].zfill(REAL_RANGE)), 2) + 1

    def to_signed(self, a):
        self.C = 1 if a >= REAL_MAX else 0
        a = a if self.C == 0 else a % REAL_MAX
        return a if MAX_NUM > a >= -MAX_NUM else -self.to_unsigned(a)

    def add(self, a, b):
        a = a if a >= 0 else self.to_unsigned(a)
        b = b if b >= 0 else self.to_unsigned(b)
        return self.to_signed(a + b)

    def sub(self, a, b):
        a = a if a >= 0 else self.to_unsigned(a)
        b = b if b >= 0 else self.to_unsigned(b)
        return self.add(a, self.to_unsigned(b))

    def asr(self, a):
        return self.div(a, 2)

    def div(self, a, d):
        self.C = a % d
        return a // d

    def mod(self, a, d):
        return a % d

    def calc_op(self, left, right, op_type):
        operations = {ADD: self.add, SUB: self.sub, CMP: self.sub, DIV: self.div, MOD: self.mod}

        func = operations.get(op_type)

        if not func:
            raise Exception("INCORRECT BINARY OPERRATION")

        return func(left, right)

    def calc_nop(self, res, op_type):
        operation_dict = {
            ASL: lambda: self.add(res, res),
            ASR: lambda: self.asr(res),
            INC: lambda: self.add(res, 1),
            DEC: lambda: self.sub(res, 1),
        }

        if op_type not in operation_dict:
            raise Exception("INCORRECT UNARY OPERATION")

        return operation_dict[op_type]()

    def calc(self, left, right, op_type, change_flags=False):
        is_left_char = True if isinstance(left, str) else False
        left = ord(left) if is_left_char else int(left)
        C = self.C

        if right is None:
            res = left
            is_right_char = False
            res = self.calc_nop(res, op_type)
        else:
            is_right_char = True if isinstance(right, str) else False
            right = ord(right) if is_right_char else int(right)
            res = self.calc_op(left, right, op_type)
        if change_flags:
            self.set_flags(res)
        else:
            self.C = C
        if is_left_char or is_right_char:
            res = chr(res)
            if is_left_char:
                left = chr(left)
        return left if op_type == "cmp" else res


class DataPath:
    registers = {"AC": 0, "AR": 0, "IP": 0, "SP": 0, "PS": 0, "DR": 0, "CR": 0}

    def __init__(self, input_buffer):
        self.registers["PS"] = 2
        self.output_buffer = []
        self.mem_size = MAX_ADDR + 1
        self.memory = [{VALUE: 0}] * self.mem_size
        self.alu = ALU()
        self.input_buffer = input_buffer

    def get_reg(self, reg):
        return self.registers[reg]

    def set_reg(self, reg, val):
        self.registers[reg] = val

    def wr(self):
        self.memory[self.registers["AR"]] = {VALUE: self.registers["DR"]}
        if self.registers["AR"] == OUTPUT_MAP:
            self.output_buffer.append(chr(self.registers["DR"]))
            logger.info("OUTPUT " + str(self.output_buffer[-1]))

    def rd(self):
        addr = self.registers["AR"]
        if addr == INPUT_MAP:
            if len(self.input_buffer) == 0:
                raise EOFError()
            symb = self.input_buffer.pop(0)
            self.memory[addr] = {VALUE: ord(symb)}
            logger.info("INPUT " + str(symb))
        self.registers["DR"] = self.memory[addr][VALUE]


class ControlUnit:
    def __init__(self, program, data_path, start_address, input_data, limit):
        self.program = program
        self.data_path = data_path
        self.limit = limit
        self.instr_counter = 0

        self.sig_latch_reg("IP", start_address)
        self._tick = 0
        self._map_instruction()

        self.input_data = input_data
        self.input_pointer = 0

    def _map_instruction(self):
        for i in self.program:
            self.data_path.memory[int(i["index"])] = i

    def get_reg(self, reg):
        return self.data_path.get_reg(reg)

    def sig_latch_reg(self, reg, val):
        self.data_path.set_reg(reg, val)

    def sig_write(self):
        self.data_path.wr()

    def sig_read(self):
        self.data_path.rd()

    def calc(self, left, right, op, change_flags=False):
        res = self.data_path.alu.calc(left, right, op, change_flags)
        if change_flags:
            self.sig_latch_reg("PS", self.get_reg("PS") ^ ((self.get_reg("PS") ^ self.data_path.alu.C) & 1))
            self.sig_latch_reg(
                "PS", self.get_reg("PS") ^ ((self.get_reg("PS") ^ (self.data_path.alu.Z << 1)) & (1 << 1))
            )
            self.sig_latch_reg(
                "PS", self.get_reg("PS") ^ ((self.get_reg("PS") ^ (self.data_path.alu.N << 2)) & (1 << 2))
            )
        return res

    def tick(self, comment=""):
        self.__print__(comment)
        self._tick += 1

    def current_tick(self):
        return self._tick

    def command_cycle(self, mode="main: "):
        while self.instr_counter < self.limit:
            go_next = self.decode_and_execute_instruction(mode)
            if not go_next:
                return
            self.instr_counter += 1
        if self.instr_counter >= self.limit:
            pass
            print("Limit exceeded!")

    def instruction_fetch(self):
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("IP"), "add"))
        self.sig_latch_reg("IP", self.calc(1, self.get_reg("IP"), "add"))
        self.sig_latch_reg("CR", self.data_path.memory[self.get_reg("AR")])
        return self.get_reg("CR")

    def address_fetch(self):
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("DR"), "add"))
        self.sig_read()

    def operand_fetch(self):
        self.sig_latch_reg("AR", self.calc(0, self.get_reg("DR"), "add"))
        self.sig_read()

    def decode_and_execute_instruction(self, mode=""):
        instr = self.instruction_fetch()
        self.tick(mode + "IF: IP -> AR, IP + 1 -> IP, MEM[AR] -> DR, DR -> CR")

        opcode = instr[OPCODE]
        if OPCODE not in instr.keys():
            return False

        cycle = "EF: "
        if OPERAND in instr.keys():
            self.sig_latch_reg("DR", int(self.get_reg("CR")["operand"]))  # CR -> alu -> DR (operand only)

            if instr["address"]:
                self.address_fetch()
                self.tick(mode + "AF: CR[operand] -> DR, DR -> AR, MEM[AR] -> DR")

            self.operand_fetch()
            self.tick(mode + "OF: CR[operand] -> DR, DR -> AR, MEM[AR] -> DR")

            if opcode == LOAD:
                self.sig_latch_reg("AC", self.calc(0, self.get_reg("DR"), "add", True))
                self.tick(mode + cycle + "DR -> AC")

            elif opcode == STORE:
                self.sig_latch_reg("DR", self.calc(0, self.get_reg("AC"), "add"))
                self.sig_write()
                self.tick(mode + cycle + "AC -> DR, DR -> MEM[AR]")

            elif opcode in branch_commands:
                ind = branch_commands.index(opcode)
                flag = branch_flags[ind]
                condition = True

                if (flag is not None) and flag[0] == "!":
                    condition = eval("not self.data_path.alu." + flag[1])
                elif flag is not None:
                    condition = eval("self.data_path.alu." + flag[0])
                if condition:
                    self.sig_latch_reg("IP", self.calc(0, self.get_reg("AR"), "add"))
                    self.tick(mode + cycle + "AR -> IP")
                else:
                    self.tick(mode + cycle + "NOP")
            else:
                self.sig_latch_reg("AC", self.calc(self.get_reg("AC"), self.get_reg("DR"), opcode, True))
                self.tick(mode + cycle + "AC " + opcode + " DR -> AC")
        else:
            if opcode == HLT:
                self.tick(mode + cycle + "END OF THE SIMULATION")
                return False
            elif opcode == PUSH:
                self.sig_latch_reg("DR", self.calc(self.get_reg("AC"), 0, "add"))
                self.sig_latch_reg("AR", self.calc(self.get_reg("SP"), 0, "add"))
                self.sig_latch_reg("SP", self.calc(self.get_reg("SP"), 1, "sub"))
                self.sig_write()
                self.tick(mode + cycle + "AC -> DR, SP -> AR, SP - 1 -> SP, DR -> mem[SP]")
            elif opcode == POP:
                self.sig_latch_reg("SP", self.calc(self.get_reg("SP"), 1, "add"))  #
                self.sig_latch_reg("AR", self.calc(self.get_reg("SP"), 0, "add"))  #
                self.sig_read()
                self.sig_latch_reg("AC", self.calc(self.get_reg("DR"), 0, "add", True))
                self.tick(mode + cycle + "SP + 1 -> SP, SP -> AR, mem[SP] -> DR, DR -> AC")

            elif opcode == CLA:
                self.sig_latch_reg("AC", self.calc(self.get_reg("AC"), self.get_reg("AC"), "sub", True))
                self.tick(mode + cycle + "0 -> AC")
            elif opcode == NOP:
                self.tick(mode + cycle + "NOP")
            else:
                self.sig_latch_reg("AC", self.calc(self.get_reg("AC"), None, opcode, True))
                self.tick(mode + cycle + " " + opcode + " AC -> AC")
        return True

    def toStrIfNeeded(self, text):
        return str((lambda x: ord(x) if isinstance(x, str) else x)(text))

    def __print__(self, comment):
        state_repr = (
            "TICK: {:4} | AC {:7} | IP: {:4} | AR: {:4} | SP: {:4} | PS: {:3} | DR: {:7} | MEM[AR] {:7} | MEM[SP] {:7} | CR: {:12} |"
        ).format(
            self._tick,
            self.toStrIfNeeded(self.get_reg("AC")),
            str(self.get_reg("IP")),
            str(self.get_reg("AR")),
            str(self.get_reg("SP")),
            str(bin(self.get_reg("PS"))[2:].zfill(5)),
            self.toStrIfNeeded(self.get_reg("DR")),
            self.toStrIfNeeded(self.data_path.memory[self.get_reg("AR")][VALUE]),
            self.toStrIfNeeded(self.data_path.memory[self.get_reg("SP")][VALUE]),
            self.get_reg("CR")["opcode"]
            + (lambda x: " " + str(x["operand"]) if "operand" in x.keys() else "")(self.get_reg("CR")),
        )
        logger.info(state_repr + " " + comment)


def simulation(code, limit, input_data, start_addr):
    start_address = start_addr
    data_path = DataPath(input_data)
    control_unit = ControlUnit(code, data_path, start_address, input_data, limit)
    control_unit.command_cycle()
    return [control_unit.data_path.output_buffer, control_unit.instr_counter, control_unit.current_tick()]


def main(code, input_f):
    with open(input_f, encoding="utf-8") as file:
        input_text = file.read()
        if not input_text:
            input_token = []
        else:
            input_token = eval(input_text)
    start_addr, code = read_code(code)
    output, instr_num, ticks = simulation(
        code,
        limit=50000,
        input_data=input_token,
        start_addr=start_addr,
    )
    print(f"Output: {''.join(output)}\nInstruction number: {instr_num}\nTicks: {ticks - 1}")


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
