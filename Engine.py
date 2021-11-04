from pynput import keyboard
from typing import Callable

class Engine(object):
    KB_EVENT = ['press', 'release']
    def __init__(self, width, height, debug=False) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.debug = debug

        self._timestamp = 0
        self.map = [['*'] * width] * height
        self.end = False
    
    def start(self) -> bool:
        while not self.end:
            print(self.end)
            self.render_map()
            self._listen()
        return self._end()
    
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
    
    def subscribe_keyboard(self, key: str, event: str, callback: Callable) -> bool:
        ...
    
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
        if event.key == keyboard.Key.esc:
            self.end = True

    def log(self, message, level='debug') -> str:
        if level.lower() == 'debug' and not self.debug: return

        message = f'[ {level.upper()} ] {message}'
        print(message)
        return message