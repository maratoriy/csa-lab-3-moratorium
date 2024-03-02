from isa_header import *


def is_address(text):
    return all(c.isdigit() for c in text) and MAX_ADDR >= int(text) >= 0


def is_number(text):
    return all(c.isdigit() for c in text) and MAX_NUM > int(text) >= -MAX_ADDR


def is_address_label(text):
    return text == adr_label


def is_const_label(text):
    return text == const_label


def is_char_sym(sym):
    return ("a" <= sym <= "z") or ("A" <= sym <= "Z")


def is_num_sym(sym):
    return "0" <= sym <= "9"


def is_sym(sym):
    return is_num_sym(sym) or is_char_sym(sym) or sym == "_"


def is_code_label(text):
    if not is_char_sym(text[0]):
        return False
    return (
        (text[-1] == LABEL_DELIMETER)
        and text not in op_commands
        and all(is_sym(c) for c in text[:-1])
        and not (is_const_label(text))
    )


def is_command(text):
    return (text in op_commands) or (text in nop_commands)


def is_op_command(text):
    return text in op_commands


def is_nop_command(text):
    return text in nop_commands


def read_code(source):
    with open(source) as file:
        data = file.read()
        array_of_dicts = eval(data)
        start_addr = array_of_dicts[0][START_ADDR]
        array_of_dicts.remove(array_of_dicts[0])
    return int(start_addr), array_of_dicts


def write_code(code_target, start_address, code):
    with open(code_target, encoding="utf-8", mode="w") as f:
        f.write("[\n")
        f.write("{'" + START_ADDR + "': " + str(start_address) + " },\n")
        for i in range(len(code)):
            line = code[i]
            f.write(str(line))
            if i != len(code) - 1:
                f.write(",\n")
        f.write("]\n")
