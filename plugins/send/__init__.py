from command_handler import *

def send(text,context):
    group,_,text = text.partition(" ")
        # Add edge case when group or text is empty
        # Add edge case when no group with such name is found
    subprocess.run([
            "curl",
            "-X", "PUT",
            "-H", "Content-Type: text/plain",
            "--data", text,
            f"https://rekini.tgt.lv/{group}",
        ], check=True)
    return


def register(register_command):
    root = Path(__file__).parent / "config.txt"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",send)

#register command
register(register_command)
