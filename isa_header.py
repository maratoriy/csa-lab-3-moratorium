# BRANCH COMMANDS
JMP = "jmp"
JMN = "jmn"
JMNN = "jmnn"
JMZ = "jmz"
JMNZ = "jmnz"
JMC = "jmc"
JMNC = "jmnc"

# FLAGS
FLAG_NONE = None
FLAG_N = "N"
FLAG_NOT_N = "!N"
FLAG_Z = "Z"
FLAG_NOT_Z = "!Z"
FLAG_C = "C"
FLAG_NOT_C = "!C"

# OP COMMANDS
ADD = "add"
SUB = "sub"
LOAD = "load"
STORE = "store"
CMP = "cmp"
DIV = "div"
MOD = "mod"

# NOP COMMANDS
HLT = "hlt"
CLA = "cla"
ASL = "asl"
ASR = "asr"
INC = "inc"
DEC = "dec"
NOP = "nop"
PUSH = "push"
POP = "pop"

branch_flags = [FLAG_NONE, FLAG_N, FLAG_NOT_N, FLAG_Z, FLAG_NOT_Z, FLAG_C, FLAG_NOT_C]
branch_commands = [JMP, JMN, JMNN, JMZ, JMNZ, JMC, JMNC]
op_commands = [ADD, SUB, LOAD, STORE, CMP, DIV, MOD] + branch_commands
nop_commands = [HLT, NOP, ASL, ASR, INC, DEC, CLA, PUSH, POP]

# cpu params
NUMERIC_RANGE = 31
ADDR_RANGE = 12
MAX_ADDR = (1 << ADDR_RANGE) - 1
MAX_NUM = 1 << NUMERIC_RANGE

REAL_MAX = MAX_NUM * 2
REAL_RANGE = NUMERIC_RANGE + 1

INPUT_MAP = MAX_ADDR - 1
OUTPUT_MAP = MAX_ADDR

# struct
adr_label = "org"
const_label = "word:"
start_label = "start"

# translator keys
START_ADDR = "start_addr"
OPERAND = "operand"
OPCODE = "opcode"
INDEX = "index"
VALUE = "value"
LABEL_DELIMETER = ":"
