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
from pynput import keyboard

class Item(object):
    EVENT = ['enter', 'leave', 'timeout', 'removed']

    def __init__(self, name, x, y, create_time, symbol='*', life=None, hidden=False) -> None:
        super().__init__()
        self.name = name
        self.x = x
        self.y = y
        self.created = create_time
        self.life = life
        self.symbol = symbol
        self.hidden = hidden

        self._callback = {e: [] for e in self.EVENT}
        self._timer = {}
    
    def position(self) -> list:
        return [self.x, self.y]
    
    def show(self, flag: bool):
        self.hidden = not flag
    
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


class Engine(object):
    KB_EVENT = ['press', 'release']
    EVENT = []
    CONTROL_KEY = {
        # Make sure you know what you are doing when changing these properties 
        keyboard.Key.up: 'up', 
        keyboard.Key.down: 'down', 
        keyboard.Key.right: 'right', 
        keyboard.Key.left: 'left'
    }

    def __init__(self, width, height, move, debug=False) -> None:
        super().__init__()

        self.width = width
        self.height = height
        self.move_cb = move
        self.debug = debug

        self.character = [int(height/2), int(width/2)] # x, y
        self.map = [[None for _ in range(width)] for _ in range(height)]
        self.isend = False

        self._timestamp = 0
        self._kb_callback = {e: defaultdict(list) for e in self.KB_EVENT}
        self._subscription = {e: [] for e in self.EVENT}

    def start(self) -> bool:
        while not self.isend:
            self.render_map()
            while not self._listen(): pass
            self._next()

    def end(self) -> None:
        self.isend = True
        self._cleanup()
        return True

    # Movement
    def position(self, x: int = None, y: int = None) -> Tuple[int,int]:
        if x is not None: self.character[0] = x
        if y is not None: self.character[1] = y
        return self.character[:]

    def move(self, direction) -> None:
        x, y = self.move_cb(direction, *self.position())
        self.position(x, y)
        self.log(f'move to {x}, {y}')

    # Map
    def render_map(self) -> None:
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

    def update_map(self) -> bool:
        # [ TODO ]
        ...

    # Subscriber
    def add_item(self, name: str, x: int, y: int, symbol: str, hidden: bool = False, life: int = None) -> Item:
        if len(symbol) > 1:
            self.log(f'Item symbol can only be a single character. Received "{symbol}"', 'error')
            self.log(f'Item not added', 'warn')
            return None
        
        if len(symbol) == 0:
            self.log('Symbol is automatically transformed into space', 'warn')
            symbol = ' '

        new_item = Item(name, x, y, self._timestamp, symbol, life, hidden)

        if self.map[x][y] is not None:
            self.log(f'Original item on ({x}, {y}) is replaced', 'warn')
            self._clean_tile(x, y)
        self.map[x][y] = new_item
        self.log(f'Item {name} is added to ({x}, {y})')

        return new_item
    
    def remove_item(self, x: int = None, y: int = None, name: str = None) -> bool:
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

    def add_event(self) -> bool:
        # [ TODO ]
        ...
    
    def subscribe_keyboard(self, key: str, action: str, callback: Callable) -> bool:
        """ Subscribe to a certain keyboard event. 
        The key name of special keys be the same as pynput keycode: 
          https://pynput.readthedocs.io/en/stable/keyboard.html?highlight=key#pynput.keyboard.Key
        """
        if action not in self.KB_EVENT: 
            self.log(f'action "{action}" not allowed. Callback not subscribed', 'warn')
            self.log(f'Available actions: {self.KB_EVENT}', 'warn')
            return False

        if key in keyboard.Key._member_names_:
            key = itemgetter(key)(keyboard.Key)
        else:
            key = keyboard.KeyCode.from_char(key)
        self._kb_callback[action][key].append(callback)
        self.log(f'event "{action} {key}" subscribed')
        return True

    def unsubscribe_keyboard(self, key: str, action: str, callback: Callable) -> bool:
        """ Unsubscribe the first occurence of given callback """
        if action not in self.KB_EVENT: 
            self.log(f'action "{action}" not found', 'warn')
            return False
        if callback not in self._kb_callback[action][key]:
            self.log(f'callback {callback.__name__} not found', 'warn')
            return False

        self._kb_callback[action][key].remove(callback)
        return True
    
    def subscribe(self, event: str, callback: Callable) -> bool:
        """ Subscribe to a global event.
        Available event: 'movement'
        """
        # if event not in self.EVENT: 
        #     self.log(f'action "{event}" not allowed. Callback not subscribed', 'warn')
        #     self.log(f'Available actions: {self.EVENT}', 'warn')
        #     return False
        
        # self._subscription[event].append(callback)
        # return True
        ...
    
    def unsubscribe(self, event: str, callback: Callable) -> bool:
        """ Unsubscribe the first occurence of given callback """
        # if event not in self.EVENT: 
        #     self.log(f'event "{event}" not found', 'warn')
        #     return False
        # if callback not in self._kb_callback[event]:
        #     self.log(f'callback {callback.__name__} not found', 'warn')
        #     return False

        # self._subscription[event].remove(callback)
        # return True
        ...
    
    def timer(self) -> bool:
        # [ TODO ]
        ...
    
    # utilities
    def _next(self) -> int:
        self._timestamp += 1
        self._check_event()
        return self._timestamp
    
    def _cleanup(self) -> bool:
        print('\n - end - \n')
        return True
    
    def _listen(self) -> bool:
        with keyboard.Events() as events:
            event = events.get()
            self.log('Received event {}'.format(event))
            updated = self._handle_keyboard(event)
        return updated

    def _handle_keyboard(self, event) -> bool:
        flag = False
        action = type(event).__name__.lower()

        if action == 'press' and event.key in self.CONTROL_KEY:
            self.move(self.CONTROL_KEY[event.key])
            flag = True
        for cb in self._kb_callback[action][event.key]:
            cb(self)
            flag = True
        return flag
    
    def _check_event(self):
        for rid, cid, item in self._get_items():
            if rid == self.character[0] and cid == self.character[1]:
                item.fire('enter')
            
            alive = item.check_alive(self._timestamp)
            if not alive:
                self._clean_tile(rid, cid)
        
    
    def _get_tile(self, x: int, y: int) -> str:
        if x == self.character[0] and y == self.character[1]:
            return 'x'
        item = self.map[x][y]
        return item.symbol if item and not item.hidden else ' '
    
    def _get_items(self) -> Tuple[int,int,Item]:
        for rid, row in enumerate(self.map):
            for cid, item in enumerate(row):
                if item: yield rid, cid, item
    
    def _clean_tile(self, x: int, y: int) -> bool:
        item = self.map[x][y]
        if not item: return False
        item.fire('removed')
        self.map[x][y] = None
        self.log(f'Item {item.name} is removed')
        return True
    
    def _print_map(self):
        """ For debugging """
        for row in self.map:
            self.log(row)

    def log(self, message, level='debug') -> str:
        if level.lower() == 'debug' and not self.debug: return

        message = f'[ {level.upper()} ] {message}'
        print(message)
        return message