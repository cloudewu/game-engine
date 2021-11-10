"""
[Map]
x/y 0 -> 1
0
v
1
"""

from operator import itemgetter
from collections import defaultdict
from typing import Callable, Tuple
import random
PYNPUT_AVAILABLE = True
try:
    from pynput import keyboard
except ImportError:
    PYNPUT_AVAILABLE = False

from .base import BaseObject

class Item(BaseObject):
    EVENT = ['enter', 'leave', 'timeout', 'removed']

    def __init__(self, name, x, y, create_time, symbol='*', life=None, block=False, hidden=False, debug=False) -> None:
        super().__init__(debug)
        self.name = name
        self.x = x
        self.y = y
        self.created = create_time
        self.life = life
        self.symbol = symbol
        self.block = block
        self.hidden = hidden

        self.istouched = False

        self._callback = {e: [] for e in self.EVENT}
        self._timer = {}
    
    def position(self) -> list:
        return [self.x, self.y]
    
    def show(self, flag: bool = True) -> None:
        self.hidden = not flag
        return
    
    def add_event(self, action: str, callback: Callable) -> bool:
        if action not in self.EVENT:
            self.log(f'action "{action}" not allowed. Event not registered', 'warn')
            self.log(f'Available actions: {self.EVENT}', 'warn')
            return False
        
        self._callback[action].append(callback)
        return True

    def remove_event(self, action: str, callback: Callable) -> bool:
        if action not in self.EVENT:
            self.log(f'action "{action}" not found', 'warn')
            return False
        if callback not in self._callback[action]:
            self.log(f'callback {callback.__name__} not found', 'warn')
            return False

        self._callback[action].remove(callback)
        return True
    
    def timer(self, time: int, callback: Callable) -> int:
        id = random.randint(1000, 10000)
        self._timer[id] = [time, callback]
        return id

    def tik_timer(self) -> None:
        dead = []
        for id, obj in self._timer.items():
            obj[0] -= 1
            if obj[0] <= 0:
                dead.append(id)
        for id in dead:
            self.fire('timeout', id)
    
    def remove_timer(self, id: int) -> bool:
        if id not in self._timer:
            self.log(f'timer {id} not found ({self.name})', 'warn')
            return False
        del self._timer[id]
        return True
    
    def fire(self, action: str, *args) -> bool:
        if action not in self.EVENT:
            self.log(f'action "{action}" not exist. Event not fired', 'warn')
            return False

        if action == 'timeout':
            self._timer[args[0]][1](self)
            del self._timer[args[0]]
        elif action == 'enter':
            self.istouched = True
        elif action == 'leave':
            self.istouched = False

        for cb in self._callback[action]:
            cb(self)
        return True
    
    def check_alive(self, timestamp) -> bool:
        """ Daily update """
        if self.life and (timestamp > self.created + self.life):
            self.hidden = True
            return False
        self.tik_timer()
        return True


class Engine(BaseObject):
    KB_EVENT = ['press', 'release']
    DEFAULT_EVENT = ['onstart', 'update_map', 'step_end', 'onend']
    CONTROL_KEY = {
        # default key for stdin
        'w': 'up',
        's': 'down',
        'a': 'left',
        'd': 'right',
        # default key for pynput
        **({
            keyboard.Key.up: 'up', 
            keyboard.Key.down: 'down', 
            keyboard.Key.right: 'right', 
            keyboard.Key.left: 'left'
        } if PYNPUT_AVAILABLE else {})
    }

    def __init__(self, width, height, move_function, input = None, map_renderer = None, debug = False) -> None:
        super().__init__(debug)

        self.width = width
        self.height = height
        self.move_cb = move_function
        self.input = input

        self.character = [int(height/2), int(width/2)] # x, y
        self.map = [[None for _ in range(width)] for _ in range(height)]
        self.backpack = ['apple']
        self.isend = False

        self._timestamp = 0
        self._kb_callback = {e: defaultdict(list) for e in self.KB_EVENT}
        self._subscription = {e: [] for e in self.DEFAULT_EVENT}
        self._layer_renderer = {'map': map_renderer or self.default_map_renderer}
        self._timer = {}

        self.layer = 'map'
        self.renderer = self._layer_renderer[self.layer]
        if not self.input:
            self.input = 'pynput' if PYNPUT_AVAILABLE else 'stdin'
            self.log(f'Autodetect input system: {self.input}')
        self.log(self.CONTROL_KEY)

    def start(self) -> int:
        """ Start the game loop. 
        The current timestamp is yielded in real-time, right before rendering the map.  
        The game loop is:
        1. announce current timestamp (yield)
        2. render the map
        3. listen to any events and handle valid ones
        4. fire `end_step` event
        5. back to (1)
        """
        self.fire('onstart')
        while not self.isend:
            yield self._timestamp
            self.renderer(self)
            while not self._listen(): pass
            self._next()
        yield None

    def end(self) -> None:
        """ End the game immediately """
        self.isend = True
        self.fire('onend')
        self._cleanup()
        return True

    ### ------ MOVEMENT FUNCTIONALITIES ------ ###

    def position(self, x: int = None, y: int = None) -> Tuple[int,int]:
        """ Get or set the character's position.
        @return character's position after updated.
        """
        # [TODO] multiple characters
        if x is not None: self.character[0] = x
        if y is not None: self.character[1] = y
        return self.character[:]

    def move(self, direction) -> None:
        x, y = self.move_cb(direction, *self.position())
        if self.map[x][y] and self.map[x][y].block:
            self.log(f'block by item')
            return
        self.position(x, y)
        self.log(f'move to {x}, {y}')
        return

    ### ------ MAP FUNCTIONALITIES ------ ###

    def add_layer(self, name: str, renderer: Callable, switch = False, force_update = False) -> None:
        """ Add a new layer of the game.
        @param name - the name of new layer
        @param renderer - the render function of this layer
        @param switch - whether to switch to this layer immediately after it's created
        @param force_update - whether to force the engine render re-render current layer immediately
        """
        if name in self._layer_renderer.keys():
            self.log(f'layer {name} already exist. Renderer overridden.', 'warn')
        
        self._layer_renderer[name] = renderer
        if switch or force_update:
            self.layer = name
            self.renderer = renderer
        if force_update:
            self.renderer()
        return

    def change_to_layer(self, name: str) -> bool:
        """
        @return `true` if the switching is successful.
        """
        if name not in self._layer_renderer.keys():
            self.log(f'layer {name} is not avaliable', 'error')
            self.log(f'available layer list: {str(list(self._layer_renderer.keys()))}', 'debug')
            return False
        
        self.layer = name
        self.renderer = self._layer_renderer[name]
        self.log(f'switch to layer {self.layer} with handler {self.renderer.__name__}')
        return True
    
    def default_map_renderer(self, *args) -> None:
        print()
        print(f'time: {self._timestamp:3}')
        print('.', '-' * self.width, '.', sep='')
        for i in range(self.height):
            print('|', end='')
            for j in range(self.width):
                symbol = self._get_tile(i, j)
                print(symbol, end='')
            print('|')
        print('\'', '-' * self.width, '\'', sep='')
        return

    def update_map(self, items) -> bool:
        """ Update a selection of tiles at once """
        # [ TODO ]
        ...

    def add_item(self, name: str, x: int, y: int, symbol: str, block: bool = False, hidden: bool = False, life: int = None) -> Item:
        """ Add an item (tile) on to the map.
        @return created `Item` object
        """
        if len(symbol) > 1:
            self.log(f'Item symbol can only be a single character. Received "{symbol}"', 'error')
            self.log(f'Item not added', 'warn')
            return None
        
        if len(symbol) == 0:
            self.log('Symbol is automatically transformed into space', 'warn')
            symbol = ' '

        new_item = Item(name, x, y, self._timestamp, symbol, life, block, hidden, debug=self.debug)

        if self.map[x][y] is not None:
            self.log(f'Original item on ({x}, {y}) is replaced', 'warn')
            self._clean_tile(x, y)
        self.map[x][y] = new_item
        self.log(f'Item {name} is added to ({x}, {y})')

        return new_item
    
    def remove_item(self, x: int = None, y: int = None, name: str = None) -> bool:
        """
        @return `true` if an item is removed.
        """
        if (x or y) and not (x and y):
            self.log(f'(x, y) should be specified at the same time', 'error')
            return False
        
        if x and not name:
            self._clean_tile(x, y)
            return True

        if x:
            if not self.map[x][y]:
                return False
            if self.map[x][y].name == name: 
                self._clean_tile[x][y]
                return True
            return False
        
        flag = False
        for rid, cid, item in self._get_items():
            if item.name == name:
                self._clean_tile(rid, cid)
                flag = True
        return flag

    def timer(self, time: int, callback: Callable) -> int:
        """
        @return timer id
        """
        id = random.randint(1000, 10000)
        self._timer[id] = [time, callback]
        self.log(f'timer {id} is added')
        return id

    def tik_timer(self) -> None:
        """ Check existing timers """
        # [TODO-REFACT]
        dead = []
        for id, obj in self._timer.items():
            obj[0] -= 1
            if obj[0] <= 0:
                obj[1](self)
                dead.append(id)
        for id in dead:
            self.remove_timer(id)
    
    def remove_timer(self, id: int) -> bool:
        """
        @return `true` if the timer is successfully removed.
        """
        if id not in self._timer:
            self.log(f'timer {id} not found ({self.name})', 'warn')
            return False
        del self._timer[id]
        self.log(f'timer {id} is removed')
        return True

    ### ------ EVENT FUNCTIONALITIES ------ ###

    def fire(self, event: str, *args) -> bool:
        if event not in self._subscription.keys():
            self.log(f'event "{event}" not exist. Event not fired', 'warn')
            return False

        for cb in self._subscription[event]:
            cb(self)
        return True

    def add_event(self, name: str) -> bool:
        if name in self._subscription.keys():
            self.log(f'event {name} already existed.', 'warn')
            return False
        
        self._subscription[name] = []
        self.log(f'event {name} is added')
        return True
    
    def subscribe(self, event: str, callback: Callable) -> bool:
        if event not in self._subscription.keys():
            self.log(f'Event "{event}" not exists. Callback not subscribed', 'warn')
            self.log(f'Available events: {list(self._subscription.keys())}', 'warn')
            return False
    
        self._subscription[event].append(callback)
        self.log(f'callback {callback.__name__} is subscribed to event {event}')
        return True

    def unsubscribe(self, event: str, callback: Callable) -> bool:
        if event not in self._subscription.keys():
            self.log(f'event "{event}" not found', 'warn')
            return False
        if callback not in self._subscription[event]:
            self.log(f'callback {callback.__name__} not found', 'warn')
            return False

        self._subscription[event].remove(callback)
        self.log(f'callback {callback.__name__} is unsubscribed from the event {event}')
        return True

    def subscribe_keyboard(self, key: str, action: str, callback: Callable) -> bool:
        """ Subscribe to a certain keyboard event.  
        If stdin is used, the event will be subscribed to the exact string input ('esc' string, rather than `Esc` key);  
        or if pynput is used, the event will be bound to a single keypress (`Esc` key).  
        The key name of special keys be the same as pynput keycode if pynput is used: 
          https://pynput.readthedocs.io/en/stable/keyboard.html?highlight=key#pynput.keyboard.Key
        """
        if self.input == 'stdin': # only press is available for stdin
            action = 'press'
        elif key in keyboard.Key._member_names_:
            key = itemgetter(key)(keyboard.Key)
        else:
            key = keyboard.KeyCode.from_char(key)

        if action not in self.KB_EVENT: 
            self.log(f'action "{action}" not allowed. Callback not subscribed', 'warn')
            self.log(f'Available actions: {self.KB_EVENT}', 'warn')
            return False

        self._kb_callback[action][key].append(callback)
        self.log(f'event "{action} {key}" subscribed')
        return True

    def unsubscribe_keyboard(self, key: str, action: str, callback: Callable) -> bool:
        """ Unsubscribe the first occurence of given callback """
        if self.input == 'stdin': # only press is available for stdin
            action = 'press'
        elif key in keyboard.Key._member_names_:
            key = itemgetter(key)(keyboard.Key)
        else:
            key = keyboard.KeyCode.from_char(key)

        if action not in self.KB_EVENT: 
            self.log(f'action "{action}" not found', 'warn')
            return False
        if callback not in self._kb_callback[action][key]:
            self.log(f'callback {callback.__name__} not found', 'warn')
            return False
        
        self._kb_callback[action][key].remove(callback) # stdin
        self.log(f'event "{action} {key}" unsubscribed')
        return True
    
    ### ------ UTILITIES ------ ###

    def _next(self) -> int:
        """ Called when a step ends """
        self._timestamp += 1
        self._check_event()
        self.tik_timer()
        self.fire('step_end')
        return self._timestamp
    
    def _cleanup(self) -> bool:
        """ Called after the game ends """
        print('\n - end - \n')
        return True
    
    def _listen(self) -> bool:
        """ 
        Listen to user action and map events to corresponding handlers.
        @return `True` if a valid event is detected.
        """
        updated = None
        if self.input == 'pynput':
            with keyboard.Events() as events:
                event = events.get()
                self.log('Received event {} (pynput)'.format(event))
                updated = self._handle_keyboard(event)
        elif self.input == 'stdin':
            event = input().lower()
            self.log('Received input {} (stdin)'.format(event))
            updated = self._handle_stdin(event)
        else:
            self.log(f'Selected input system {self.input} not supported.', 'error')
            self.end()
        return updated

    def _handle_stdin(self, key: str) -> bool:
        """ Handle events from standard input """
        flag = False
        if self.layer == 'map' and key in self.CONTROL_KEY:
            self.move(self.CONTROL_KEY[key])
            flag = True

        for cb in self._kb_callback['press'][key]:
            cb(self)
            flag = True
        return flag

    def _handle_keyboard(self, event) -> bool:
        """ Handle events from pynput """
        flag = False
        action = type(event).__name__.lower()

        if self.layer == 'map' and action == 'press' and event.key in self.CONTROL_KEY:
            self.move(self.CONTROL_KEY[event.key])
            flag = True
        for cb in self._kb_callback[action][event.key]:
            cb(self)
            flag = True
        return flag
    
    def _check_event(self) -> None:
        """ Check global events, including timers, item events, etc. """
        for rid, cid, item in self._get_items():
            if rid == self.character[0] and cid == self.character[1]:
                item.fire('enter')
            elif item.istouched:
                item.fire('leave')
            
            alive = item.check_alive(self._timestamp)
            if not alive:
                self._clean_tile(rid, cid)
    
    def _get_tile(self, x: int, y: int) -> str:
        """ Get the tile symbol of a certain position """
        if x == self.character[0] and y == self.character[1]:
            return 'x'
        item = self.map[x][y]
        return item.symbol if item and not item.hidden else ' '
    
    def _get_items(self) -> Tuple[int,int,Item]:
        """
        Yield all existing items.
        @return (x, y, item)
        """
        for rid, row in enumerate(self.map):
            for cid, item in enumerate(row):
                if item: yield rid, cid, item
    
    def _clean_tile(self, x: int, y: int) -> bool:
        """
        Remove the item on a certain tile
        @return `true` if an item is removed
        """
        item = self.map[x][y]
        if not item: return False
        item.fire('removed')
        self.map[x][y] = None
        self.log(f'Item {item.name} is removed')
        return True
    
    def _print_map(self):
        """ Print all objects on the map array. Just for debugging """
        for row in self.map:
            self.log(row)