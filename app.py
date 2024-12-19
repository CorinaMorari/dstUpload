import os
from pyembroidery import *

# Function to read DST file, extract info, set needles, and generate a new DST file
def get_dst_info(dst_file_path):
    # Read the DST file
    pattern = read(dst_file_path)

    # Extract basic information
    stitches = len(pattern.stitches)
    thread_list = pattern.threadlist
    thread_colors = [{"r": thread.get_red(), "g": thread.get_green(), "b": thread.get_blue()} for thread in pattern.threadlist]

    # Analyze match commands
    needle_set_count = 0
    color_change_count = 0
    needle_number = 0
    color_change_commands = []
    set_needle = False  # Flag to indicate if the next stitch should set the needle number
    needle_set_info = []  # To store the set needle numbers and their positions

    # Handle color changes as implicit needle changes
    for command in pattern.get_match_commands(COLOR_CHANGE):
        color_change_count += 1
        color_change_command = command  # Store the current COLOR_CHANGE command

        # Add the color_change_command to the list
        color_change_commands.append(color_change_command)
        print(f"COLOR_CHANGE command at stitch {command}")

    # Update needle set commands in the pattern based on color change
    for inx, stitch in enumerate(pattern.stitches):
        if set_needle or inx == 0:
            set_needle = False
            # Use color change as needle change (if machine supports this behavior)
            stitch[2] = EmbConstant.COLOR_CHANGE | needle_number  # Adjust for color change
            needle_set_info.append({"needle_number": needle_number, "stitch_position": inx})
            needle_number += 1  # Increment the needle number
            print(f"Set needle {needle_number} at stitch {inx}")

        # Check if the current stitch matches any color change command
        for color_change_command in color_change_commands:
            if stitch == color_change_command:
                set_needle = True
                print(f"Stitch {stitch} matches color change command at position {color_change_command}")

    # Save the modified pattern to a new DST file
    new_dst_file_path = 'updated_pattern.dst'
    write(pattern, new_dst_file_path)

    return {
        "stitches": stitches,
        "thread_list": thread_list,
        "thread_colors": thread_colors,
        "needle_set_count": needle_set_count,
        "color_change_count": color_change_count,
        "needle_set_info": needle_set_info,
        "new_dst_file": new_dst_file_path
    }
