import string
import csv
import sys
import re

# Global variables
name = "MySymbol"
font = 1.27
size = (0, 0)
step = 0
side = 'L'
num = 1
dnum = 1
direction = 0
x, y = 0, 0
pos_cache = {}  # Cache for storing positions based on size
props = {} # properties

keywords=['name:', 'size:', 'sizep:', 'step:', 'side:', 'num:', 'rnum:', 'font:', 'prop:']

def split_by_whitespace_or_comma(s):
    return re.split(r'[,\s]\s*', s)

def parse_line(line):
    parts = line.split()
    if parts[0] in keywords:
        return parts[0][:-1], ' '.join(parts[1:])
    else:
        return 'pin', parts

def update_globals(key, value):
    global size, step, side, num, x, y, name, props, dnum
    if key == 'size':
        new_size = tuple(map(float, split_by_whitespace_or_comma(value)))
        size = new_size
    if key == 'sizep':
        new_size = tuple(map(float, split_by_whitespace_or_comma(value)))
        size = (round(new_size[0]/2+1)*2 * step,
                round(new_size[1]/2+1)*2 * step )
        #print(step)
        #print(size)
    elif key == 'step':
        step = float(value)
    elif key == 'font':
        font = float(value)
    elif key == 'side':
        reset_position(value)
        side = value
    elif key == 'num':
        num = int(value)
        dnum = 1
    elif key == 'rnum':
        num = int(value)
        dnum = -1
    elif key == 'name':
        name = value
    elif key == 'prop':
        a = re.split(r'[,\s]\s*', value, maxsplit=1)
        if(len(a) == 2):
            props[a[0]] = a[1]

def cache_current_position():
    global pos_cache, side, x, y, direction
    pos_cache[side] = (x, y, direction)

def reset_position(new_side):
    global pos_cache, size, x, y, step, direction, side
    if(side == new_side):
        return;
    if new_side in pos_cache:
        x, y, direction = pos_cache[new_side]
    else:
        if(side != ''):
            cache_current_position()
        #print(size)
        if new_side == 'L':
            x = -size[0] / 2 - step
            y = size[1] / 2  - step
            direction = 0
        elif new_side == 'R':
            x = size[0] / 2 + step
            y = size[1] / 2 - step
            direction = 180
        elif new_side == 'T':
            x = -size[0] / 2 + step
            y = size[1] / 2  + step
            direction = 270
        elif new_side == 'B':
            x = -size[0] / 2 + step
            y = -size[1] / 2 - step 
            direction = 90
        #print(f'{x} {y} {direction}')

def calculate_position():
    global x, y, num
    position = (x, y)
    if side in ['L', 'R']:
        y -= step
    else:  # 'T' or 'B'
        x += step
    return position

prop_pos = 0

def print_prop(prop_name, val, col=-1, row=-1, hide=True):
    global props, font, prop_pos

    display = "hide"
    x = font
    y = prop_pos
    if(row != -1):
        y = round(size[1] / 2 + step - (step*row), 2)
    if(col != -1):
        x = round(-size[0] / 2 + step + (step*col), 2)

    if(not hide):
        display = "(justify left)"

    s = f'    (property "{prop_name}" "{val}" (at {x} {y:.2f} 0)\n' \
        f'      (effects (font (size {font} {font})) {display})\n' \
        f'    )\n'

    prop_pos = y - step*2
    return s

def generate_rectangle_record(_name, step, size):
    global props, name

    TLx, TLy = round(-size[0] / 2, 2), round(size[1] / 2, 2)
    BRx, BRy = round(size[0] / 2, 2), round(-size[1] / 2, 2)

    s = ""

    for key, prop_v in props.items():
       row = -1
       col = -1
       hide = (key != "Reference")
       if(key == "Reference"):
           row = 1
           col = 0
       if(key == "Value"):
           name = prop_v
           _name = prop_v
           continue
       s += print_prop(key, prop_v, col, -1, hide)

    s += print_prop("Value", name, row=0, hide=False)

    return s + \
           f'    (symbol "{name}_0_1"\n' \
           f'      (rectangle (start {TLx:.2f} {TLy:.2f}) (end {BRx:.2f} {BRy:.2f})\n' \
           f'        (stroke (width {round(step/10, 3):.2f}) (type default))\n' \
           f'        (fill (type background))\n' \
           f'      )\n' \
           f'    )\n'

def generate_pin_records(name, step, pin_data):
    pin_records = ''
    for num, pin_name, pin_type, x, y, direction in pin_data:
        x_rounded = round(x, 2)
        y_rounded = round(y, 2)
        step_rounded = round(step, 2)
        #step_half_rounded = round(step / 2, 2)
        pin_records += f'      (pin {pin_type} line (at {x_rounded:.2f} {y_rounded:.2f} {direction} ) (length {step_rounded:.2f})\n' \
                       f'        (name "{pin_name}" (effects (font (size {font:.2f} {font:.2f}))))\n' \
                       f'        (number "{num}" (effects (font (size {font:.2f} {font:.2f}))))\n' \
                       f'      )\n'
    return f'    (symbol "{name}_1_1"\n' + pin_records + '\n    )\n'


pin_type_map = {
    'i': 'input',
    'o': 'output',
    'io': 'bidirectional',
    'vin': 'power_in',
    'v': 'power_in',
    'n': 'passive',
    '-': 'passive',
    'vout': 'power_out',
    'nc': 'no_connect'
}

def map_pin_type(pin_type):
    global pin_type_map
    #print(pin_type)
    s = pin_type_map.get(pin_type.lower(), pin_type)
    #print(s)
    return s


pins = [ 8, 13, 13, 13, 13, 9 ]

def process_file(input_file, output_file):
    global num, dnum, direction, prop_pos, size
    update_globals("side", "L")
    update_globals("step", 2.54)
    update_globals("font", 1.27)
    update_globals("sizep", "12 12")
    results = []
    for j in range(max(pins)):
        letter = string.ascii_lowercase[j]
        for row_num in range(len(pins)):
            col_count = pins[row_num]
            if j < col_count:
                for k in range(2): # c or o
                    loc = ["c", "o"][k]
                    pin_name = f"{row_num+1}{letter}_{loc}"
                    #print(pin_name)
                    pin_type = "-"
                    pin_type = map_pin_type(pin_type)
                    position = calculate_position()
                    results.append([pin_name, pin_name, pin_type,
                        round(position[0], 2), round(position[1], 2), direction])
                    num += dnum
    #sys.exit(0)


    """
    with open(input_file, 'r') as infile:
        for line in infile:
            line = line.strip()
            if(len(line) == 0):
                continue
            if(line[0] == '#'):
                continue
            #if(line == '-' or line == '--'):
            #    calculate_position()
            #    continue
            key, value = parse_line(line)
            if key != 'pin':
                update_globals(key, value)
            else:  # Treat as a pin name-type pair
    """

    #print(results)

    if output_file:
        with open(output_file, 'w', newline='') as outfile:
            csv_writer = csv.writer(outfile)
            csv_writer.writerow(['Pin Number', 'Pin Name', 'Pin Type', 'Position X', 'Position Y', 'Direction'])
            csv_writer.writerows(results)
    else:
        #print('Pin Number, Pin Name, Pin Type, Position X, Position Y', 'Direction')
        #for row in results:
        #    print(', '.join(map(str, row)))

        prop_pos = round(size[1] / 2, 2) + step

        print( f'(kicad_symbol_lib (version 20220914) (generator make_kicad_sym.py)\n' \
               f'  (symbol "{name}" (in_bom yes) (on_board yes)\n')

        print(generate_rectangle_record(name, step, size))
        print(generate_pin_records(name, step, results))

        print( f'  )\n)\n')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("    python kicad_symbol_generator.py <input_file> > <output_file.kicad_sym>")
        print("       or")
        print("    python kicad_symbol_generator.py <input_file> <output_file.csv>")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        process_file(input_file, output_file)
