from pathlib import Path
import unittest
import yaml
from jinja2 import Environment


class HomeAssistantTests(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load(Path('examples/homeassistant-fc980rs.yaml').read_text())
        self.fan = self.config['template'][0]['fan'][0]
        self.env = Environment()

    def render(self, text, **kwargs):
        return self.env.from_string(text).render(**kwargs)

    def test_all_percentage_boundaries(self):
        actions = self.fan['set_percentage'][0]['else']
        command = actions[0]['data']['command']
        for percentage, speed in [(1,1),(16,1),(17,2),(33,2),(34,3),(50,3),
                                  (51,4),(66,4),(67,5),(83,5),(84,6),(100,6)]:
            self.assertEqual(self.render(command, percentage=percentage), f'speed{speed}')
        self.assertEqual(self.fan['turn_off'][0]['data']['command'], 'off')
        self.assertEqual(self.fan['set_percentage'][0]['then'][0]['data']['command'], 'off')

    def test_turn_on_uses_stored_speed_or_one(self):
        text = self.fan['turn_on'][0]['data']['command']
        for value, expected in [('0','speed1'),('unknown','speed1'),('50','speed3'),('100','speed6')]:
            self.assertEqual(self.render(text, states=lambda _: value), expected)

    def test_turn_on_preserves_quantized_helper_values(self):
        command = self.fan['turn_on'][0]['data']['command']
        value = self.fan['turn_on'][2]['data']['value']
        # HA serializes the helper to finite decimal precision, sometimes above
        # the exact fraction; ceiling that value would advance to the next speed.
        for speed in range(1, 7):
            stored = format(speed * 100 / 6, '.15g')
            states = lambda _: stored
            self.assertEqual(self.render(command, states=states), f'speed{speed}')
            self.assertAlmostEqual(float(self.render(value, states=states)), speed * 100 / 6)

    def test_every_rest_action_checks_response_before_updating_helpers(self):
        def walk(value):
            if isinstance(value, list):
                for i, action in enumerate(value):
                    if isinstance(action, dict) and action.get('action') == 'rest_command.living_room_fan_control':
                        self.assertEqual(action['response_variable'], 'fan_response')
                        guard = value[i+1]
                        self.assertEqual(guard['condition'], 'template')
                        for status, outcome in [(200, 'True'), (400, 'False'), (503, 'False')]:
                            self.assertEqual(self.render(guard['value_template'], fan_response={'status':status,'content':{'status':'transmitted'}}),outcome)
                    walk(action)
            elif isinstance(value, dict):
                for nested in value.values(): walk(nested)
        walk(self.fan)
