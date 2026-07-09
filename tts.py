import subprocess
import os

MODEL_DIR = "models"

def voice(text, language):
    switcher = {
        "en": "en_US-lessac-medium.onnx",
        "ru": "ru_RU-dmitri-medium.onnx",
        "lv": "lv_LV-aivars-medium.onnx"
    }

    model_name = switcher.get(language, "en_US-lessac-medium.onnx")
    model_path = os.path.join(MODEL_DIR, model_name)

    result = subprocess.run(
        [
            "piper",
            "--model", model_path
        ],
        input=text.encode("utf-8"),
        capture_output=True
    )

    return result.stdout