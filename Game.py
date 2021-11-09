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

def backpack_renderer(game: Engine):
    print()
    print('---------------------------------')
    print('You are in your backpack!')
    print(game.backpack) # access all properties in game
    print('---------------------------------')
    print()

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
Game = Engine(WIDTH, HEIGHT,  # The map size of your game
              move, # The movement controller
              # map_renderer, # write your own map renderer (use this only when you are confident about what you are doing)
              debug = True
             )

# DEMO: custom layer
Game.add_layer('backpack', backpack_renderer)

# DEMO: remove item by location
item = Game.add_item('star', 3, 20, '*')
item.add_event('removed', lambda i: print('*** (1) I am removed qq ***'))
Game.remove_item(x = item.x, y = item.y)

# DEMO: remove item by name
item = Game.add_item('star', 3, 20, '*')
item.add_event('removed', lambda i: print('*** (2) I am removed qq ***'))
Game.remove_item(name = item.name)

# DEMO: item
item = Game.add_item('dollar',       # item name
                     x = 4, y = 15,  # item location
                     symbol = '$',   # what to show on screen
                     block = False,  # if the item blocks players
                     hidden = True,  # should the item be rendered
                     life = 10       # how many rounds should the item be automatically removed
                     )
item.timer(5, lambda i: i.show(True)) # show the item after 5 rounds
item.add_event('removed', lambda i: print('*** (3) I am removed qq ***'))
item.add_event('enter', lambda i: print('*** You found me! ***'))
item.add_event('leave', lambda i: print('*** You leaved me qwq *** '))

# DEMO: default events
Game.subscribe('onstart', lambda game: print('*** Game start ***'))
Game.subscribe('update_map', lambda game: print('*** Map updated ***'))
Game.subscribe('onend', lambda game: print('*** Game end ***'))

# DEMO: custom events
Game.add_event('itemfound')
Game.subscribe('itemfound', lambda game: print('*** An item is found!! ***'))

# DEMO: keyboard events
Game.subscribe_keyboard('esc', 'press', Game.end)
Game.subscribe_keyboard('b', 'press', lambda game: game.change_to_layer('backpack'))
Game.subscribe_keyboard('m', 'press', lambda game: game.change_to_layer('map'))

# MAIN
for day in Game.start():
    print(f' *** Day {day} *** ')
    
