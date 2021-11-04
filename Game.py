from Engine import Engine

map = [[]]

# SETUP
Game = Engine(40, 10, debug=True)

Game.subscribe_keyboard('q', 'press', lambda: print('press q'))
Game.subscribe_keyboard('esc', 'press', Game.end)

# MAIN
Game.start()
