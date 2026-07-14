from command_handler import *

# --- DEVICES --------------------------------------------------------------------------------------------------------------------------------------------------------
DEVICES = {
    "vanna_pol":      {"topic": "E98300", "relay": "POWER1", "name": "Vanna pol"},
    "boiler":         {"topic": "B52533", "relay": "POWER",  "name": "boiler"},
    "radiator_vanna": {"topic": "079256", "relay": "POWER",  "name": "Radiator vanna"},
    #"": {"topic": "", "relay": "POWER",  "name": ""},
    #"": {"topic": "", "relay": "POWER",  "name": ""}, # add devices ass needed for yourself
}

# --- DEVICE ALIASES (used for status lookups) --------------------------------------------------------------------------------------------------------------------------------------------------------
DEVICE_ALIASES = {
    "vanna_pol":      ["пол в ванной", "пол", "floor", "vanna pol", ],
    "vanna_pol_2":    ["пол 2", "floor 2", "vanna pol 2"],
    "boiler":         ["бойлер", "basement", "podval","boiler"],
    "radiator_vanna": ["радиатор", "батарея", "батарею", "radiator"],
}
# --- LIVE STATUS CACHE (populated from MQTT stat/ messages) ---
DEVICE_STATUS = {key: None for key in DEVICES}
 

# --- COMMANDS --------------------------------------------------------------------------------------------------------------------------------------------------------
COMMANDS = [
    (["включи пол в ванной", "включить пол", "turn on floor", "floor on",
      "вкл пол", "пол вкл", "включи пол"],
     "vanna_pol", "ON"),
    (["выключи пол в ванной", "выключить пол", "turn off floor", "floor off",
      "выкл пол", "пол выкл", "выключи пол"],
     "vanna_pol", "OFF"),

    (["включи подвал", "включи бойлер", "turn on boiler", "boiler on",
      "вкл подвал", "подвал вкл"],
     "boiler", "ON"),
    ([ "выключить бойлер", "выключи бойлер",  "turn off boiler", "boiler off",
      "выкл подвал", "подвал выкл"],
     "boiler", "OFF"),

    (["включи радиатор", "включить радиатор", " turn on radiator", "radiator on",
      "вкл радиатор", "радиатор вкл", "включи батарею"],
     "radiator_vanna", "ON"), 
    (["выключи радиатор", "выключить радиатор", "turn off radiator", "radiator off",
      "выкл радиатор", "радиатор выкл", "выключи батарею"],
     "radiator_vanna", "OFF"),

    (["включи свет", "включить свет", "turn on lights", "lights on", "свет вкл"],
     "vanna_pol", "ON"),
    (["выключи свет", "выключить свет", "turn off lights", "lights off", "свет выкл"],
     "vanna_pol", "OFF")
]

STATUS_KEYWORDS = ["статус", "status"]

# --- MQTT CONFIG --------------------------------------------------------------------------------------------------------------------------------------------------------
MQTT_HOST = "10.10.0.2"
MQTT_PORT = 1883
MQTT_BROKER = "e.tgt.lv"
MQTT_USERNAME = "alex"
MQTT_PASSWORD = "3RrG-+H+WG"

# --- MQTT CALLBACKS --------------------------------------------------------------------------------------------------------------------------------------------------------

def on_mqtt_connect(client, userdata, flags, rc):
    print("[MQTT] Connected to broker")
    unique_topics = set(d["topic"] for d in DEVICES.values())
    for t in unique_topics:
        client.subscribe(f"stat/{t}/+")
    print(unique_topics)
 
def on_mqtt_message(client, userdata, msg):
    print("MQTT MESSAGE:", msg.topic, msg.payload)
    parts = msg.topic.split("/")
    if len(parts) == 3 and parts[0] == "stat":
        mqtt_topic, relay = parts[1], parts[2]
        payload = msg.payload.decode(errors="replace").strip().upper()
        if payload not in ("ON", "OFF"):
            return
        for key, dev in DEVICES.items():
            if dev["topic"] == mqtt_topic and dev["relay"] == relay:
                DEVICE_STATUS[key] = payload
                print("CACHE AFTER UPDATE:", DEVICE_STATUS)
                print(f"[MQTT] Status update: {dev['name']} -> {payload}")
 

# --- MQTT SETUP --------------------------------------------------------------------------------------------------------------------------------------------------------
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
mqtt_client.loop_start()
print("[MQTT] Connected to broker")

def parse_command(text_lower):
    for keywords, device_key, action in COMMANDS:
        for kw in keywords:
            if kw in text_lower:
                return device_key, action
    return None, None
 
def find_device_by_alias(text_lower):
    # Check longer aliases first so "пол 2" wins over plain "пол"
    candidates = []
    for key, aliases in DEVICE_ALIASES.items():
        for alias in aliases:
            candidates.append((alias, key))
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    for alias, key in candidates:
        if alias in text_lower:
            return key
    return None
 
def parse_status_command(text_lower):
    if any(kw in text_lower for kw in STATUS_KEYWORDS):
        return find_device_by_alias(text_lower)
    return None

def send_mqtt(device_key, action, mqtt_client):
    device = DEVICES[device_key]
    topic = f"cmnd/{device['topic']}/{device['relay']}"
    mqtt_client.publish(topic, action, qos=0)
    print(f"[MQTT] {topic} -> {action}")
    return device["name"]
 
def request_status(text,context, answer = 1, timeout=2.0):
    """Ask the device for its current state and wait briefly for the reply."""
    # find device key using text 
    # text contains command
    # example : status boiler

    device_key = find_device_by_alias(text)

    device = DEVICES[device_key]
    topic = f"cmnd/{device['topic']}/{device['relay']}"
    mqtt_client.publish(topic, "", qos=0)  # empty payload = query current state
    start = time.time()
    while time.time() - start < timeout:
        if DEVICE_STATUS.get(device_key) is not None:
            if(not answer):
                return DEVICE_STATUS[device_key]
        time.sleep(0.1)
    print("PLUGIN STATUS CACHE:", DEVICE_STATUS)
    state = DEVICE_STATUS[device_key]
    device_name = device_key
    if state:
        state_ru = "включён" if state == "ON" else "выключен"
        reply_to_channel(f"<b>{text}</b> сейчас: <b>{state_ru}</b>",context)
    else:
        reply_to_channel(f"Нет ответа от <b>{text}</b> повторите попытку скоро.",context)
    return

def command_handler(text,context):
    device_key, action = parse_command(text.lower())
    if device_key:
        device_name = DEVICES[device_key]["name"]
        current_state = request_status(text,context,0)

        if current_state == action:
            state_ru = "уже включён" if action == "ON" else "уже выключен"
            reply_to_channel( 
                f"<b>{device_name}</b> {state_ru} ",
                context
            )
        else:
            #send_mqtt(device_key, action)
            action_ru = "включён" if action == "ON" else "выключен"
            reply_to_channel(
                f"<b>{device_name}</b> {action_ru}",
                context
            )
        return

def get_mqtt(stop = 0):
    if stop:
        print("Returning mqtt client...")
        return mqtt_client

def register(register_command):
    for status_kw in STATUS_KEYWORDS:
        register_command(f"{status_kw.strip()}",request_status)

    for keywords, device_key, action in COMMANDS:
        for keyword in keywords:
            register_command(f"{keyword.strip()}",command_handler)
    register_command(f"get_mqtt",get_mqtt)

#register command
register(register_command)

