from flask import Flask, render_template

from modules.weather import get_weather

app = Flask(__name__)


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
    app.run(host="0.0.0.0", port=8000, debug=True)
