from command_handler import *

def parrot(text,context):
    print(text)
    context["mumble"].channels.find_by_name(context["mumble_setting"][4]).send_text_message(text)


def register(register_command):
    root = Path(__file__).parent / "config.txt"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",parrot)

#register command
register(register_command)
