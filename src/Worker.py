import time
import requests

from PyQt5.QtCore import QThread
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot

class Worker(QThread):
    """Background thread which polls the SC2 Client API and emits signals
    containing the game data when joining or leaving a game
    """

    enter_game = pyqtSignal(dict)
    exit_game  = pyqtSignal(dict)
    in_game    = False

    def run(self):

        while True:
            try:
                # Query the API
                r = requests.get("http://localhost:6119/game")
                gameResponse = r.json()

                # Determine if we're in game
                in_game = (
                    gameResponse['players'][0]['result'] == "Undecided" and
                    gameResponse['isReplay'] == "false"
                )

                # We've entered a game
                if in_game and not self.in_game:
                    self.enter_game.emit(gameResponse)

                # We've left a game
                elif not in_game and self.in_game:
                    self.exit_game.emit(gameResponse)

                self.in_game = in_game

            except Exception as e:
                print("%s: %s" % (e.__class__.__name__, e))

            time.sleep(1)
