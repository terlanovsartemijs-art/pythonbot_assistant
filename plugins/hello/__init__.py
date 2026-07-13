from command_handler import *


def hello():
    print("Hello")

def register(register_command):
    root = Path(__file__).parent / "config.txt"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",hello)

#register command
register(register_command)
