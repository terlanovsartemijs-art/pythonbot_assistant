from command_handler import *

def parrot(text,context):
    print(text)
    context["mumble"].channels.find_by_name(context["mumble_settings"][4]).send_text_message(text)
    reply_to_channel(text,context)


def register(register_command):
    root = Path(__file__).parent / "config"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",parrot)

#register command
register(register_command)
