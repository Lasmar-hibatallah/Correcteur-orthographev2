import os
import sys

BASE = os.path.abspath(".")
print("BASE =", BASE)

print("\nContenu de ./grammalecte :")
print(os.listdir("grammalecte"))

print("\nContenu de ./grammalecte/grammalecte :")
print(os.listdir("grammalecte/grammalecte"))
