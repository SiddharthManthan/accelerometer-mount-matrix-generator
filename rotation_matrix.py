#!/usr/bin/python3

import glob
import os

"""
(according to Android emulator, seems to be inverse for iio)
upright/normal: 0 9.81 0
upside down: 0 -9.81 0
to the left (right side up): 9.81 0 0
to the right (left side up): -9.81 0 0
lying flat (screen up): 0 0 9.81
lying flat (screen down): 0 0 -9.81
"""

POS_LOOKUP_TABLE = [
    "right-up",
    "normal",
    "screen-up"
]

NEG_LOOKUP_TABLE = [
    "left-up",
    "bottom-up",
    "screen-down"
]


def multiply_matrix(X, Y):
    result = [[0] * len(Y)] * len(X)
    # iterate through rows of X
    for i in range(len(X)):
       # iterate through columns of Y
       for j in range(len(Y[0])):
           # iterate through rows of Y
           for k in range(len(Y)):
               result[i][j] += X[i][k] * Y[k][j]
    return result


def read_sysfs_int(path):
    with open(path) as handle:
        return int(handle.read().strip())


def read_sysfs_float(path):
    with open(path) as handle:
        return float(handle.read().strip())


def guess_sysfs_name(device):
    if os.path.isfile(os.path.join(device, 'name')):
        with open(os.path.join(device, 'name')) as handle:
            return handle.read().strip()

    if os.path.islink(device):
        sys_device = os.readlink(device)
        driver = sys_device.split('/')[-2]
        return driver
    return "Unknown"


def read_accel_from_device(device):
    x_raw = read_sysfs_int(os.path.join(device, 'in_accel_x_raw'))
    y_raw = read_sysfs_int(os.path.join(device, 'in_accel_y_raw'))
    z_raw = read_sysfs_int(os.path.join(device, 'in_accel_z_raw'))
    scale = read_sysfs_float(os.path.join(device, 'in_accel_scale'))
    x = x_raw * scale
    y = y_raw * scale
    z = z_raw * scale
    status = x + y + z != 0
    value = "{}, {}, {} g".format(round(x, 2), round(y, 2), round(z, 2))
    print(value)
    return [x, y, z]

def get_extreme_value_index(values):
    max_value = max(values)
    min_value = min(values)
    # Return the most extreme value
    if max_value > -min_value:
        return (max_value, values.index(max_value))
    else:
        return (min_value, values.index(min_value))


def do_stuff(rotation_matrix, accel_matrix, index):
    extr_value, extr_index = get_extreme_value_index(accel_matrix)
    row = [0] * 3
    if extr_value > 0:
        row[index] = -1
    else:
        row[index] = 1

    rotation_matrix[extr_index] = row
    return rotation_matrix


def main():
    for device in glob.glob('/sys/bus/iio/devices/iio:device*'):
        if os.path.isfile(os.path.join(device, 'in_accel_x_raw')):
            model = guess_sysfs_name(device)
            print("Model: " + model)

            # Initialize a 3x3 matrix
            rotation_matrix = [[0] * 3] * 3

            print("Hold your device normal")
            input("Press Enter to read...")
            matrix_normal = read_accel_from_device(device)

            print("Rotate your device to the left (so the right side is up)")
            input("Press Enter to read...")
            matrix_left = read_accel_from_device(device)

            print("Put your device onto the table, so the screen points up")
            input("Press Enter to read...")
            matrix_up = read_accel_from_device(device)

            rotation_matrix = do_stuff(rotation_matrix, matrix_normal, 1)
            rotation_matrix = do_stuff(rotation_matrix, matrix_left, 0)
            rotation_matrix = do_stuff(rotation_matrix, matrix_up, 2)


            #result = multiply_matrix(matrix_a, rotation_matrix)
#            for r in result:
#                print(r)
#                value, index = get_extreme_value_index(r)
#                if value > 0:
#                    direction = POS_LOOKUP_TABLE[index]
#                else:
#                    direction = NEG_LOOKUP_TABLE[index]
#                print("Assumed direction: " + direction)

            print("Generated rotation matrix:")
            for row in rotation_matrix:
                print(row)



if __name__ == '__main__':
    main()
