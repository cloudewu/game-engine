from Engine import Engine

WIDTH, HEIGHT = 40, 10

def move(action, x, y):
    if action == 'up':
        ...
    elif action == 'down':
        ...
    elif action == 'left':
        ...
    elif action == 'right':
        ...
    return [x, y]

# SETUP
Game = Engine(WIDTH, HEIGHT,  # The map size of your game
              move, # The movement controller you write
              debug=True
             )

Game.subscribe_keyboard('q', 'press', lambda: print('press q'))
Game.subscribe_keyboard('esc', 'press', Game.end)

# MAIN
Game.start()
