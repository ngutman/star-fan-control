from flask import Flask, jsonify
from control_fan import control_fan, control_fc980rs
from radio import RadioBusy, RadioError

app = Flask(__name__)


@app.route('/control/<fan_id>/<command>')
def control(fan_id: str, command: str):
    try:
        address = int(fan_id)
    except ValueError:
        return jsonify(error='Star 7 fan ID must be an integer from 0 to 31'), 400
    control_fan(fan_id=address, command=command)
    return '<p>Done!</p>'


@app.route('/control/fc980rs/<prefix>/<command>')
def control_new(prefix: str, command: str):
    control_fc980rs(prefix, command)
    return jsonify(status='transmitted', protocol='fc980rs', command=command)


@app.get('/health')
def health():
    # Liveness only: deliberately does not transmit or reset the shared radio.
    return jsonify(status='ok')


@app.errorhandler(ValueError)
def invalid_command(error):
    return jsonify(error=str(error)), 400


@app.errorhandler(RadioBusy)
def radio_busy(error):
    return jsonify(error=str(error)), 503, {'Retry-After': '2'}


@app.errorhandler(RadioError)
def radio_failed(error):
    app.logger.exception('Radio transmission failed')
    return jsonify(error=str(error)), 503
