import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

from modules.audio import MonopriceController, create_audio_blueprint
from modules.cameras import FrigateClient, create_camera_blueprint
from modules.weather import get_weather
from modules.home_assistant import HomeAssistantClient, create_floorplan_blueprint

load_dotenv(Path(__file__).resolve().parent / '.env', override=False)

app = Flask(__name__)
audio_controller = MonopriceController(
    port=os.environ.get("AUDIO_SERIAL_PORT", "/dev/ttyUSB0")
)
app.register_blueprint(create_audio_blueprint(audio_controller))
frigate_client = FrigateClient(
    base_url=os.environ.get("FRIGATE_URL", "http://192.168.88.120:5000"),
    live_url=os.environ.get("FRIGATE_LIVE_URL"),
    access_token=os.environ.get("FRIGATE_API_TOKEN"),
)
app.register_blueprint(create_camera_blueprint(frigate_client))
home_assistant_client = HomeAssistantClient(
    base_url=os.environ.get('HA_URL', 'http://192.168.88.56:8123'),
    access_token=os.environ.get('HA_TOKEN'),
)
app.register_blueprint(create_floorplan_blueprint(home_assistant_client))


@app.route("/")
def home():
    periods, hourly, error = get_weather()

    return render_template(
        "index.html",
        periods=periods,
        hourly=hourly,
        error=error,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
