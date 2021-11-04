from operator import itemgetter
from collections import defaultdict
from pynput import keyboard
from typing import Callable

class Engine(object):
    KB_EVENT = ['press', 'release']
    VR_KEYS = ['']

    def __init__(self, width, height, debug=False) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.debug = debug

        self._timestamp = 0
        self._kb_callback = {e: defaultdict(list) for e in self.KB_EVENT}
        self.map = [['*'] * width] * height
        self.isend = False
    
    def start(self) -> bool:
        while not self.isend:
            self.render_map()
            self._listen()
    
    def end(self) -> None:
        print('end')
        self.isend = True
        self._end()
        return True

    # Map
    def render_map(self) -> None:
        print()
        print(f'time: {self._timestamp:3}')
        print('.', '-' * self.width, '.', sep='')
        for i in range(self.height):
            print('|', end='')
            for j in range(self.width):
                print('.', end='')
            print('|')
        print('\'', '-' * self.width, '\'', sep='')
        return True

    def update_map(self) -> bool:
        ...

    # Subscriber
    def add_event(self) -> bool:
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
    
    def subscribe(self) -> bool:
        ...
    
    def timer(self) -> bool:
        ...
    
    # Movement
    def move() -> None:
        ...
    
    # utilities
    def _next(self) -> int:
        self._timestamp += 1
        return self._timestamp
    
    def _end(self) -> bool:
        print('\n - end - \n')
        return True
    
    def _listen(self) -> None:
        with keyboard.Events() as events:
            event = events.get()
            self.log('Received event {}'.format(event))
            self._handle_keyboard(event)

    def _handle_keyboard(self, event) -> None:
        action = type(event).__name__.lower()
        for cb in self._kb_callback[action][event.key]:
            cb()

    def log(self, message, level='debug') -> str:
        if level.lower() == 'debug' and not self.debug: return

        message = f'[ {level.upper()} ] {message}'
        print(message)
        return message