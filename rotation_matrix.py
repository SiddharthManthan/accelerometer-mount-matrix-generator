#!/usr/bin/python3

import glob
import os
import sys
import time

"""
(according to Android emulator, seems to be inverse for iio)
upright/normal: 0 9.81 0
upside down: 0 -9.81 0
to the left (right side up): 9.81 0 0
to the right (left side up): -9.81 0 0
lying flat (screen up): 0 0 9.81
lying flat (screen down): 0 0 -9.81
"""

NEG_LOOKUP_TABLE = [
    "right-up",
    "normal",
    "screen-up"
]

POS_LOOKUP_TABLE = [
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


def read_sysfs_mount_matrix(device):
    for filename in ["mount_matrix", "in_accel_mount_matrix"]:
        path = os.path.join(device, filename)
        try:
            with open(path) as handle:
                matrix_str = handle.read().strip()
                mount_matrix = []
                for row in matrix_str.split("; "):
                    mount_matrix.append(list(map(int, row.split(", "))))
                return mount_matrix
        except FileNotFoundError:
            pass
    raise RuntimeError("No mount matrix")


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
    scale=[None] * 3
    if os.path.exists(os.path.join(device, 'in_accel_scale')):
        scale_input = read_sysfs_float(os.path.join(device, 'in_accel_scale'))
        scale.extend([scale_input] * 3)
    else:
        scale[0]=read_sysfs_float(os.path.join(device, 'in_accel_x_scale'))
        scale[1]=read_sysfs_float(os.path.join(device, 'in_accel_y_scale'))
        scale[2]=read_sysfs_float(os.path.join(device, 'in_accel_z_scale'))
    x = x_raw * scale[0]
    y = y_raw * scale[1]
    z = z_raw * scale[2]
    return [x, y, z]


def get_extreme_value_index(values):
    max_value = max(values)
    min_value = min(values)
    # Return the most extreme value
    if max_value > -min_value:
        return (max_value, values.index(max_value))
    else:
        return (min_value, values.index(min_value))


def fill_rotation_matrix(rotation_matrix, accel_matrix, should_be_index):
    extr_value, extr_index = get_extreme_value_index(accel_matrix)
    row = [0] * 3
    if extr_value > 0:
        row[should_be_index] = -1
    else:
        row[should_be_index] = 1

    rotation_matrix[extr_index] = row
    return rotation_matrix


def generate_mount_matrix(device):
    # Initialize a 3x3 matrix
    rotation_matrix = [[0] * 3] * 3

    print("Hold your device normal (upright, so the device is vertical)")
    input("Press Enter to read...")
    matrix_normal = read_accel_from_device(device)

    print("Rotate your device to the left (so the right side is up)")
    input("Press Enter to read...")
    matrix_left = read_accel_from_device(device)

    print("Put your device onto the table, so the screen points up")
    input("Press Enter to read...")
    matrix_up = read_accel_from_device(device)

    rotation_matrix = fill_rotation_matrix(rotation_matrix, matrix_normal, 1)
    rotation_matrix = fill_rotation_matrix(rotation_matrix, matrix_left, 0)
    rotation_matrix = fill_rotation_matrix(rotation_matrix, matrix_up, 2)

    # Verify that the matrix makes sense
    for row in rotation_matrix:
        # Each row must contain two 0 and one 1 or -1
        if not (row.count(0) == 2 and (row.count(1) == 1 or row.count(-1) == 1)):
            print("ERROR: The generated rotation matrix does not make any sense!")
            break

    print("Generated rotation matrix:")
    for row in rotation_matrix:
        print(row)


def show_accel_values(device, print_raw=False, print_adjusted=False):
    accel_matrix = read_accel_from_device(device)
    if print_raw:
        print("{}, {}, {} g".format(round(accel_matrix[0], 2), round(accel_matrix[1], 2), round(accel_matrix[2], 2)))
    try:
        mount_matrix = read_sysfs_mount_matrix(device)
        result_matrix = multiply_matrix([accel_matrix], mount_matrix)
    except RuntimeError:
        # mount-matrix not found, ignore
        result_matrix = [accel_matrix]
    if print_adjusted:
        print("{}, {}, {} g".format(round(result_matrix[0][0], 2), round(result_matrix[0][1], 2), round(result_matrix[0][2], 2)))
    value, index = get_extreme_value_index(result_matrix[0])
    if value > 0:
        direction = POS_LOOKUP_TABLE[index]
    else:
        direction = NEG_LOOKUP_TABLE[index]
    return direction


def monitor_accel_values(device, print_adjusted=False):
    direction_old = ""
    while True:
        direction = show_accel_values(device, print_adjusted)
        if direction_old != direction:
            if not print_adjusted:
                print("Orientation changed: " + direction)
            direction_old = direction
        time.sleep(0.1)


def usage():
    print("Usage: " + sys.argv[0] + " generate|show|show-raw|monitor|monitor-values")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        usage()

    for device in glob.glob('/sys/bus/iio/devices/iio:device*'):
        if os.path.isfile(os.path.join(device, 'in_accel_x_raw')):
            model = guess_sysfs_name(device)
            print("Model: " + model)

            if sys.argv[1] == "generate":
                generate_mount_matrix(device)
            elif sys.argv[1] == "show":
                print("Direction: " + show_accel_values(device, print_adjusted=True))
            elif sys.argv[1] == "show-raw":
                show_accel_values(device, print_raw=True)
            elif sys.argv[1] == "monitor":
                monitor_accel_values(device)
            elif sys.argv[1] == "monitor-values":
                monitor_accel_values(device, print_adjusted=True)
            else:
                usage()

            return

    print("No accelerometer found. Exiting.")
    sys.exit(1)


if __name__ == '__main__':
    main()
