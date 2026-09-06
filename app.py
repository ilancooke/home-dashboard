import os

from flask import Flask, render_template

from modules.audio import MonopriceController, create_audio_blueprint
from modules.weather import get_weather

app = Flask(__name__)
audio_controller = MonopriceController(
    port=os.environ.get("AUDIO_SERIAL_PORT", "/dev/ttyUSB0")
)
app.register_blueprint(create_audio_blueprint(audio_controller))


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
