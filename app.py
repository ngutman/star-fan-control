from flask import Flask
from control_fan import control_fan

app = Flask(__name__)

@app.route("/control/<fan_id>/<command>")
def control(fan_id: str, command: str):
    control_fan(fan_id=int(fan_id), command=command)
    return "<p>Done!</p>"