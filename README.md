# Star 7 Remote RF Control using CC1101
This is a simple repo containing code to send RF commands to Star (https://star.co.il/) fans using a basic CC1101 Transceiver ([python-cc1101](https://github.com/fphammerle/python-cc1101/tree/master)) wired to a Raspberry PI

<img width="400" alt="image" src="https://github.com/ngutman/star-fan-control/assets/1540134/7e742ebb-1b58-4b45-b7ff-22f6fa828221">


## RF Protocol
The RF communication was recorded using [URH](https://github.com/jopohl/urh). Each remote got a few switches near the battery place that allows to change the remote "identifier", so several fans in proximity can be controlled by different remotes. 

<img width="500" alt="image" src="https://github.com/ngutman/star-fan-control/assets/1540134/971f7ce8-f1f9-41ac-8cd3-c358a577609e">

Since I had two different remotes it was rather easy to parse the control packets -

<img width="600" alt="image" src="https://github.com/ngutman/star-fan-control/assets/1540134/e6545f8e-8657-4666-916e-f2406b0d8117"> <img width="995" alt="image" src="https://github.com/ngutman/star-fan-control/assets/1540134/05597aa7-98d5-4cf7-bd5f-76cf75affedc">


- The remote baud rate is ~3300 (~300µs per symbol)
- Each bit got a carrier `10` bits - so `1101` is transmitted as `101101100101`
- The first 5 bits corresponds to the "identifier switches"
- The last 8 bits are the command
- Long-pressing a button just keeps transmitting the same packet repeatedly

### RF Commands Table

| Command | HEX |
| ------- | ---- |
| Power   | 0x84 |
| Light   | 0x82 |
| Speed 1 | 0x90 |
| Speed 2 | 0x94 |
| Speed 3 | 0xa0 |
| Speed 4 | 0xb0 |
| Speed 5 | 0xc4 |
| Speed 6 | 0xc0 |

## Using CC1101 to control the fan
After understanding the RF protocol we can use CC1101 (or any other RF transmitter/transceiver) to control the fans. Check [control_fan.py](https://github.com/ngutman/star-fan-control/blob/master/control_fan.py#L32) for more information.

## Exposing API and wiring to Home Assistant
### Python Setup + Running Flask
```bash
sudo apt install python3.11
python -m venv /home/pi/python-env
source /home/pi/python-env/bin/activate
pip3 install -r requirements.txt
flask --app app run --host=0.0.0.0 # (or gunicorn -w 2 app:app)
```

### Flask and Gunicorn

A very simple flask application is included in [app.py](https://github.com/ngutman/star-fan-control/blob/master/app.py) which exposes `/control/<fan_id>/<command>`. 

A basic [.service](https://github.com/ngutman/star-fan-control/blob/master/fan-control.service) file is included to serve the app using Gunicorn.

### Home Assistant Fan Template
Once you have the service running on your raspberry pi you can use the following configuration to wire the API to a fan template (add to your configuration.yaml) - don't forget to correctly set `YOUR_RASPBERRY_PI_ADDRESS`

```yaml
rest_command:
  fan_control:
    url: "http://<YOUR_RASPBERRY_PI_ADDRESS>:5003/control/{{fan_id}}/{{command}}"
    method: GET
    content_type: "application/x-www-form-urlencoded; charset=utf-8"

# Keep track of the fan state
input_boolean:
  bedroom_fan_state:

# Keep track of fan speed
input_number:
  bedroom_fan_percentage:
    name: Bedroom Fan Percentage
    min: 0
    max: 100

fan:
  - platform: template
    fans:
      bedroom_fan:
        friendly_name: "Bedroom Fan"
        unique_id: bedroom_fan
        value_template: "{{ states('input_boolean.bedroom_fan_state') }}"
        percentage_template: >
          {{ states('input_number.bedroom_fan_percentage') }}
        turn_on:
          - service: rest_command.fan_control
            data:
              command: "speed3"
              fan_id: "28"
          - service: input_boolean.turn_on
            target:
              entity_id: input_boolean.bedroom_fan_state
          - service: input_number.set_value
            target:
              entity_id: input_number.bedroom_fan_percentage
            data:
              value: 50
        turn_off:
          - service: rest_command.fan_control
            data:
              command: "power"
              fan_id: "28"
          - service: input_number.set_value
            target:
              entity_id: input_number.bedroom_fan_percentage
            data:
              value: 0
          - service: input_boolean.turn_off
            target:
              entity_id: input_boolean.bedroom_fan_state
        set_percentage:
          - service: rest_command.fan_control
            data_template:
              command: >
                {% if percentage < 17 %} speed1
                {% elif percentage < 34 %} speed2
                {% elif percentage < 51 %} speed3
                {% elif percentage < 67 %} speed4
                {% elif percentage < 84 %} speed5
                {% else %} speed6
                {% endif %}
              fan_id: "28"
          - service: input_number.set_value
            target:
              entity_id: input_number.bedroom_fan_percentage
            data:
              value: "{{ percentage }}"
        speed_count: 6
```

### If All Goes Well
You should have a fan entity, possibily exposed to HomeKit as well!

<img width="1021" alt="image" src="https://github.com/ngutman/star-fan-control/assets/1540134/b57e2d95-6094-4c6f-af41-7d118efb1c62">
<img width="590" alt="image" src="https://github.com/ngutman/star-fan-control/assets/1540134/8f8113d3-9d94-4ad8-9afc-8227ee823523">


