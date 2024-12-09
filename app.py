from pyembroidery import Embroidery, Thread, Design, Color

# Create threads based on color numbers (e.g., color code '1000' is a red thread in some systems)
thread_1 = Thread(Color('1756'))  # Example: thread color with number
thread_2 = Thread(Color('1553'))  # Another color code for blue

# Create a design (start with an empty design)
design = Design()

# Add some stitches with threads
design.add_stitch(10, 10, thread=thread_1)  # Thread 1
design.add_stitch(20, 20, thread=thread_2)  # Thread 2

# Save the design as a DST file
with open("output.dst", "wb") as f:
    design.save(f)

# Thread information (can be used separately in documentation or software)
print(f"Thread 1 is color: {thread_1.color}, Thread 2 is color: {thread_2.color}")
