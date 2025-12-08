import pymunk
import inspect

print(f"Pymunk version: {pymunk.version}")
print(f"Pymunk file: {pymunk.__file__}")

print("\nSpace attributes:")
for attr in dir(pymunk.Space):
    if "collision" in attr:
        print(f"  {attr}")

print("\nHelp on on_collision:")
try:
    help(pymunk.Space.on_collision)
except AttributeError:
    print("on_collision not found")

print("\nHelp on add_collision_handler:")
try:
    help(pymunk.Space.add_collision_handler)
except AttributeError:
    print("add_collision_handler not found")
