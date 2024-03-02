#!/usr/bin/python3
import sys

from isa import *

labels = {}
start_address = -1


def split_q(string, splitter=" "):
    result = []
    in_quotes = False
    current_word = ""
    for char in string:
        if char == splitter and not in_quotes:
            if current_word:
                result.append(current_word)
                current_word = ""
        elif char == "'":
            in_quotes = not in_quotes
            current_word += char
        else:
            current_word += char
    if current_word:
        result.append(current_word)
    return result


def is_label_string(arr):
    return (
        len(arr) >= 2
        and is_code_label(arr[0])
        and (is_op_string(arr[1:]) or is_nop_string(arr[1:]))
        or is_const_string(arr[1:])
    )


def is_labeless_string(arr):
    return len(arr) <= 2 and (is_op_string(arr) or is_nop_string(arr))


def is_direct_addr(addr):
    return is_address(addr) or (addr in labels.keys())


def is_indirect_addr(addr):
    return (
        addr[0] == "("
        and addr[-1] == ")"
        and (is_address(addr[1 : len(addr) - 1]) or addr[1 : len(addr) - 1] in labels.keys())
    )


def is_op_string(arr):
    return len(arr) == 2 and is_op_command(arr[0]) and (is_direct_addr(arr[1]) or is_indirect_addr(arr[1]))


def is_nop_string(arr):
    return len(arr) == 1 and is_nop_command(arr[0])


def not_empty(arr):
    return [s for s in arr if s != ""]


def is_pstr(arr):
    str_arr = not_empty("".join(arr[1:]).split("'"))
    num_arr = not_empty(arr[0].split(","))
    return len(num_arr) == 1 and is_number(num_arr[0]) and len(str_arr) == 1 and len(str_arr[0]) == int(num_arr[0])


def is_const_string(arr):
    return (
        len(arr) >= 2
        and is_const_label(arr[0])
        and ((is_number(arr[1]) or arr[1] in labels.keys()) or is_pstr(arr[1:]))
    )


def is_address_string(arr):
    return len(arr) == 2 and is_address_label(arr[0]) and is_address(arr[1])


def make_op_string(arr, index):
    is_indirect = False
    if is_indirect_addr(arr[1]):
        arr[1] = arr[1][1 : len(arr[1]) - 1]
        is_indirect = True
    return [
        {
            INDEX: index,
            OPCODE: arr[0],
            OPERAND: int(labels[arr[1]]) if arr[1] in labels else int(arr[1]),
            VALUE: 0,
            "address": is_indirect,
        }
    ]


def nop_string(arr, index):
    return [{INDEX: index, OPCODE: arr[0], VALUE: 0}]


def const_string(arr, index):
    if is_pstr(arr[1:]):
        str_arr = not_empty("".join(arr[2:]).split("'"))
        str_arr = str_arr[0]
        num = int(not_empty(arr[1].split(","))[0])
        cur = 1
        lines = [{INDEX: index, VALUE: num, OPCODE: NOP}]
        while cur <= num:
            lines.append({INDEX: index + cur, VALUE: ord(str_arr[cur - 1]), OPCODE: NOP})
            cur += 1
        return lines

    return [{INDEX: index, VALUE: int(labels[arr[1]]) if arr[1] in labels else int(arr[1]), OPCODE: NOP}]


def asm_to_json(arr, index):
    if is_label_string(arr):
        if is_op_string(arr[1:]):
            return make_op_string(arr[1:], index)
        elif is_const_string(arr[1:]):
            return const_string(arr[1:], index)
        else:
            return nop_string(arr[1:], index)
    elif is_labeless_string(arr):
        if is_op_string(arr):
            return make_op_string(arr, index)
        elif is_nop_string(arr):
            return nop_string(arr, index)
    elif is_const_string(arr):
        return const_string(arr, index)
    else:
        return {}


def traverse_labels(arr, index):
    global start_address
    lbl = arr[0]
    if is_code_label(lbl):
        lbl = lbl[: len(lbl) - 1]
        assert lbl not in labels.keys(), "LABELS MUST BE UNIQUE " + str(lbl) + " " + str(labels.keys())
        if lbl == start_label:
            start_address = index
        labels[lbl] = index
        if is_const_string(arr[1:]) and is_pstr(arr[2:]):
            return index + int(not_empty(arr[2].split(","))[0]) + 1
        else:
            return index + 1
    else:
        if is_const_string(arr) and is_pstr(arr[1:]):
            return index + int(not_empty(arr[1].split(","))[0]) + 1
        else:
            return index + 1


def translate(text):
    pc = 0
    sz = len(text)
    source_code = []
    translated_code = []
    for i in range(sz):
        if not text[i]:
            continue
        text[i] = split_q(text[i], ";")[0]
        line = text[i]
        source_code.append(line)
        code_str = split_q(line)
        if is_address_string(code_str):
            pc = int(code_str[1])
            continue
        pc = traverse_labels(code_str, pc)

    pc = 0
    for line in source_code:
        code_str = split_q(line)
        if is_address_string(code_str):
            pc = int(code_str[1])
            continue
        translated = asm_to_json(code_str, pc)
        assert not translated == {}, ("INCORRECT SOURCE CODE LINE " + str(pc) + ': "' + str(line)) + '"'
        for tr_str in translated:
            translated_code.append(tr_str)
            pc = int(tr_str[INDEX])
        pc += 1

    assert start_label in labels.keys()
    is_ended = False
    for instr in translated_code:
        if OPCODE in instr.keys() and instr[OPCODE] == HLT:
            is_ended = True
    assert is_ended, "PROGRAM MUST HAVE HLT COMMAND"
    return translated_code


def main(code_source, code_target):
    with open(code_source, encoding="utf-8") as f:
        code_source = f.read().split("\n")
    code = translate(code_source)
    write_code(code_target, start_address, code)
    global labels
    labels = {}
    print("LINES OF CODES:", len(code_source), "NUMBER OF INSTRUCTIONS:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Bad arguments: translator.py *input_file* *output_file*"
    _, source, target = sys.argv
    main(source, target)
