import sys
import os
import json
import requests

from pathlib import Path
from PyQt5 import QtWidgets
from PyQt5 import uic


BASE_URL      = "https://api.twitch.tv/helix"
CLIENT_ID     = "83ucn1dvrgjjd7lc0ak8q9snzzb9oc" # Client IDs are public :)
CONFIG_PATH   = "%s/foresee.json" % str(Path.home())
CONFIG_FIELDS = [
    'oauth',
    'prediction_name',
    'submission_period',
]


class MainWindow(QtWidgets.QMainWindow):

    # Dict with the ID and outcome IDs of the active prediction
    prediction = None


    def __init__(self, worker):
        super(MainWindow, self).__init__()

        # Find and load the UI file. PyInstaller binaries run from a
        # tempfile identified in _MEIPASS, so we may need to look there...
        base_path = getattr(sys, '_MEIPASS', os.getcwd())
        uic.loadUi(base_path + '/MainWindow.ui', self)

        # Load the settings from the config file
        self.load_config()

        # Connect the enter game/exit game signals from the worker
        worker.enter_game.connect(self.enter_game)
        worker.exit_game.connect(self.exit_game)

        # Set up the UI text fields to save the config file when values change
        for key in CONFIG_FIELDS:
            try:
                getattr(self, key).textChanged.connect(self.save_config)

            except Exception as e:
                print("Error updating UI - %s: %s" % (e.__class__.__name__, e))

        self.show()


    def enter_game(self, game):
        """Enter Game event
        Create a Twitch prediction using the players names as options
        """

        # We only care about 1v1 games for now
        if len(game['players']) != 2:
            return

        config = self.get_config()

        # Get the broadcaster id from the oauth token
        # The broadcaster ID must match the oauth user
        try:
            user_response = self.send_request("GET", "/users")
            user_id  = user_response['data'][0]['id']

        except Exception as e:
            print("Error getting user info, check OAuth key - %s: %s" % (e.__class__.__name__, e))
            return

        # Create the prediction
        prediction_response = self.send_request(
            "POST",
            "/predictions",
            {
                'broadcaster_id': user_id,
                'title': config['prediction_name'],
                'outcomes': [
                    {
                        'title': game['players'][0]['name']
                    },
                    {
                        'title': game['players'][1]['name']
                    }
                ],
                'prediction_window': int(config['submission_period'])
            }
        )

        # Store the prediction/outcome_ids to update later
        try:
            self.prediction = {
                'id': prediction_response['data'][0]['id'],
                'user_id': user_id,
                'outcome_ids': [
                    prediction_response['data'][0]['outcomes'][0]['id'],
                    prediction_response['data'][0]['outcomes'][1]['id'],
                ]
            }

        except Exception as e:
            print("Error setting active prediction - %s: %s" % (e.__class__.__name__, e))


    def exit_game(self, game):
        """Exit Game event
        Resolve the Twitch prediction with the winning outcome id
        """

        if not self.prediction:
            return

        # Set the outcome id for the winner
        winning_outcome_id = None

        if game['players'][0]['result'] == "Victory":
            winning_outcome_id = self.prediction['outcome_ids'][0]

        elif game['players'][1]['result'] == "Victory":
            winning_outcome_id = self.prediction['outcome_ids'][1]


        # Resolve the prediction
        if winning_outcome_id:
            self.send_request(
                "PATCH",
                "/predictions",
                {
                    'broadcaster_id': self.prediction['user_id'],
                    'id': self.prediction['id'],
                    'status': "RESOLVED",
                    'winning_outcome_id': winning_outcome_id,
                }
            )

        else:
            # Neither player won, maybe a tie? Cancel the prediction
            self.send_request(
                "PATCH",
                "/predictions",
                {
                    'broadcaster_id': self.prediction['user_id'],
                    'id': self.prediction['id'],
                    'status': "CANCELED",
                }
            )

        # Clear the active prediction
        self.prediction = None


    def send_request(self, method, url, data = None, headers = {}):
        """Send a request to the Twitch API.

        method (str): The HTTP verb to use. Can be any verb supported by `requests`
        url (str): The path to request on the Twitch API, eg "/user"
        data (dict): The request body
        headers (dict): Any headers to add to the request

        Returns:
            (dict): The parsed response
        """

        # Try to get the requests function for the method
        action = getattr(requests, method.lower(), None)
        if action:
            config = self.get_config()

            _headers = {
                'Authorization': "Bearer %s" % config['oauth'],
                'Client-Id':     CLIENT_ID,
                'Content-Type':  "application/json",
            }

            # Add the caller headers
            _headers.update(headers)

            # Make the request
            response = action(
                url=BASE_URL + url,
                headers=_headers,
                data=json.dumps(data)
            )

            # Return the parsed response
            return json.loads(response.content)


    def get_config(self):
        """Returns a dictionary containing the current config values"""

        return {
            key: getattr(self, key).text()
            for key in CONFIG_FIELDS
        }


    def load_config(self):
        """Loads the config from file, and updates the UI fields"""

        # Try to load the config from file
        try:
            with open(CONFIG_PATH) as json_file:
                config = json.load(json_file)

                # Update the UI fields with the config values
                for key in CONFIG_FIELDS:
                    try:
                        getattr(self, key).setText(
                            config.get(key, "")
                        )

                    except Exception as e:
                        print("Error setting UI field - %s: %s" % (e.__class__.__name__, e))

        except Exception as e:
            print("Error loading config file - %s: %s" % (e.__class__.__name__, e))
            return


    def save_config(self):
        """Saves the current values from the UI into the config file"""

        config = self.get_config()

        try:
            with open(CONFIG_PATH, 'w+') as outfile:
                json.dump(config, outfile, indent=4, sort_keys=True)

        except Exception as e:
            print("Error saving config file - %s: %s" % (e.__class__.__name__, e))
