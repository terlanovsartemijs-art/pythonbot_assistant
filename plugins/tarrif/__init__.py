from command_handler import *

# --- NORDPOOL CONFIG --------------------------------------------------------------------------------------------------------------------------------------------------------
NORDPOOL_AREA = "LV"
NORDPOOL_CURRENCY = "EUR"
NORDPOOL_TZ = ZoneInfo("Europe/Riga")

def get_nordpool_price():
    """Return (price_cents_per_kwh, interval_start, interval_end, next_price_cents, next_start, next_end)."""
    now = datetime.now(NORDPOOL_TZ)
    date_str = now.strftime("%Y-%m-%d")
    url = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices"
    params = {
        "date": date_str,
        "market": "DayAhead",
        "deliveryArea": NORDPOOL_AREA,
        "currency": NORDPOOL_CURRENCY,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[NORDPOOL] Request failed: {e}")
        return None, None, None, None, None, None

    entries = data.get("multiAreaEntries", [])
    for i, entry in enumerate(entries):
        try:
            start = datetime.fromisoformat(entry["deliveryStart"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
            end = datetime.fromisoformat(entry["deliveryEnd"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
        except Exception:
            continue
        if start <= now < end:
            price_mwh = entry.get("entryPerArea", {}).get(NORDPOOL_AREA)
            if price_mwh is None:
                continue
            price_cents = (price_mwh / 1000) * 100  # EUR/MWh -> cents/kWh

            next_price_cents, next_start, next_end = None, None, None
            if i + 1 < len(entries):
                next_entry = entries[i + 1]
                try:
                    next_start = datetime.fromisoformat(next_entry["deliveryStart"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
                    next_end = datetime.fromisoformat(next_entry["deliveryEnd"].replace("Z", "+00:00")).astimezone(NORDPOOL_TZ)
                    next_price_mwh = next_entry.get("entryPerArea", {}).get(NORDPOOL_AREA)
                    if next_price_mwh is not None:
                        next_price_cents = (next_price_mwh / 1000) * 100
                except Exception:
                    pass

            return price_cents, start, end, next_price_cents, next_start, next_end

    return None, None, None, None, None, None

def tarif(text,context):
    now = datetime.now()
    minutes_left = 15 - (now.minute % 15)
    result = f" ближайшие {minutes_left}  минут "
    price_cents, start, end, next_price_cents, next_start, next_end = get_nordpool_price(context["nordpool_config"][0],context["nordpool_config"][1],context["nordpool_config"][2])
    price_cents, start, end, next_price_cents, next_start, next_end = get_nordpool_price(context["nordpool_config"][0],context["nordpool_config"][1],context["nordpool_config"][2])
    if price_cents is not None:
        reply = (
            f" {result}"
            f" цена :  {price_cents:.2f} цента за киловатт час"
        )
    if next_price_cents is not None:
        reply += f" | следующиe 15 минут: {next_price_cents:.2f} цента за киловатт час"
        context["mumble"].channels.find_by_name(context["mumble_setting"][4]).send_text_message(reply)
    else:
        context["mumble"].channels.find_by_name(context["mumble_setting"][4]).send_text_message(
        "Could not fetch the current Nordpool tariff."
        )
    return

def register(register_command):
    root = Path(__file__).parent / "config.txt"
    with open(root,"r") as fp:
        for line in fp:
            register_command(f"{line.strip()}",tarif)

#register command
register(register_command)
