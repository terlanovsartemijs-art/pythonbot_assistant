from command_handler import *

def reload(text,context):
    print("Plugin text : " + text)
    reload_plugin(text,PLUGINS_FOLDER)
    reply_to_channel(f"Plugin : {text} reloaded/updated !",context)


def register(register_command):
    root = Path(__file__).parent / "config"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",reload)

#register command
register(register_command)
