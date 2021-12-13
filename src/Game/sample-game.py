from Game.core import Engine

# Kind reminder to TA: Don't release your code on web ;D
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

# DEMO: custom map renderer (set in Engine initialization)
def map_renderer(game):
    print()
    print(f'time: {game._timestamp:3}')
    print('.', '-' * game.width, '.', sep='')
    for i in range(game.height):
        print('|', end='')
        for j in range(game.width):
            print('x', end='')
        print('|')
    print('\'', '-' * game.width, '\'', sep='')
    return


# SETUP
WIDTH, HEIGHT = 40, 10
game = Engine(WIDTH, HEIGHT,                 # The map size of your game
              move,                          # The movement controller you write
              # init_x = 0,                  # initial x position of character
              # init_y = 1,                  # initial y position of character
              # input = 'stdin',             # the input system (default to autodetected system)
              # pixel_width = 2,             # the width of every pixel during the rendering (default to 1)
              # character_char = '⭐',       # symbol for your character (default to 'x')
              # map_filler = '..',           # what character to fill you empty map (default to ' ')
              # map_renderer = map_renderer, # write your own map renderer 
                                             # (use this only when you are confident about what you are doing)
              debug = True                   # open the debug mode
             )

# DEMO: custom layer
def backpack_renderer(game: Engine):
    print('\n---------------------------------')
    print('You are in your backpack!')
    print(game.backpack) # small showcase: you can access all properties stored in the engine
    print('---------------------------------\n')
game.add_layer('backpack', backpack_renderer)

# DEMO: item
item = game.add_item('dollar',       # item name
                     x = 4, y = 15,  # item location
                     symbol = '$',   # what to show on screen
                     block = False,  # if the item blocks players
                     hidden = True,  # should the item be rendered
                     life = 10       # how many rounds should the item be automatically removed
                     )
item.timer(5, lambda i: i.show(True)) # show the item after 5 rounds
item.subscribe('removed', lambda i: print('*** (1) I am removed qq ***'))
item.subscribe('enter', lambda i: print('*** You found me! ***'))
item.subscribe('leave', lambda i: print('*** You leaved me qwq *** '))

# DEMO: remove item by location
item = game.add_item('star', 3, 20, '*')
item.subscribe('removed', lambda i: print('*** (2) I am removed qq ***'))
game.remove_item(x = item.x, y = item.y)

# DEMO: remove item by name
item = game.add_item('star', 3, 20, '*')
item.subscribe('removed', lambda i: print('*** (3) I am removed qq ***'))
game.remove_item(name = item.name)

# DEMO: remove item by location and name (useful when you are lazy checking the current tile)
item = game.add_item('star', 3, 20, '*')
item.subscribe('removed', lambda i: print('*** (4) I am removed qq ***'))
game.remove_item(3, 30, name = 'not-star') # you should see that the item is not removed

# DEMO: default events
game.subscribe('onstart', lambda game: print('*** Game start ***'))
game.subscribe('update_map', lambda game: print('*** Map updated ***'))
game.subscribe('onend', lambda game: print('*** Game end ***'))

# DEMO: custom events
game.add_event('itemfound')
game.subscribe('itemfound', lambda game: print('*** An item is found!! ***'))

# DEMO: keyboard events
game.subscribe_keyboard('esc', 'press', lambda game: game.end())
game.subscribe_keyboard('b', 'press', lambda game: game.switch_layer('backpack'))
game.subscribe_keyboard('m', 'press', lambda game: game.switch_layer('map'))
def test(game): print('Testing keyboard :DD')
game.subscribe_keyboard('t', 'press', test)
game.unsubscribe_keyboard('t', 'press', test)

# DEMO: find item by properties
game.add_item('star1', 2, 3, '*')
game.add_item('star1', 2, 4, '*', hidden=True)
game.add_item('star2', 2, 5, '*')
game.add_item('star2', 1, 3, '&')
game.add_item('block', 1, 2, '#', block=True)
game.add_item('nil', 1, 2, '-')

all_items = game.find_item()
all_star1 = game.find_item(name='star1')
all_star_symbols = game.find_item(symbol='*')
all_blocked_item = game.find_item(block=True)
all_shown_stars = game.find_item(symbol='*', hidden=False)

# DEMO: start the game
session = game.start()
for day in session:
    if day == None: break
    # do something between steps here (add timers, subscriptions, events...)
    print(f' *** Day {day} ends *** ')
    
