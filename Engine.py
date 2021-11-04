from operator import itemgetter
from collections import defaultdict
from typing import Callable, Tuple
from pynput import keyboard

class Engine(object):
    KB_EVENT = ['press', 'release']
    EVENT = []
    CONTROL_KEY = {
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

        self.character = [int(width/2), int(height/2)]
        self.map = [['*'] * width] * height
        self.isend = False

        self._timestamp = 0
        self._kb_callback = {e: defaultdict(list) for e in self.KB_EVENT}
        self._subscription = {e: [] for e in self.EVENT}

    def start(self) -> bool:
        while not self.isend:
            self.render_map()
            self._listen()

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
        for j in range(self.height):
            print('|', end='')
            for i in range(self.width):
                if i == self.character[0] and j == self.character[1]:
                    print('x', end='')
                else:
                    print('.', end='')
            print('|')
        print('\'', '-' * self.width, '\'', sep='')
        return True

    def update_map(self) -> bool:
        # [ TODO ]
        ...

    # Subscriber
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
        return self._timestamp
    
    def _cleanup(self) -> bool:
        print('\n - end - \n')
        return True
    
    def _listen(self) -> None:
        with keyboard.Events() as events:
            event = events.get()
            self.log('Received event {}'.format(event))
            self._handle_keyboard(event)

    def _handle_keyboard(self, event) -> None:
        action = type(event).__name__.lower()

        if action == 'press' and event.key in self.CONTROL_KEY:
            self.move(self.CONTROL_KEY[event.key])
        for cb in self._kb_callback[action][event.key]:
            cb()

    def log(self, message, level='debug') -> str:
        if level.lower() == 'debug' and not self.debug: return

        message = f'[ {level.upper()} ] {message}'
        print(message)
        return message