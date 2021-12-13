from operator import itemgetter
from collections import defaultdict
from typing import Callable, Tuple
from urwid import str_util
import random
PYNPUT_AVAILABLE = True
try:
    from pynput import keyboard
except ImportError:
    PYNPUT_AVAILABLE = False

from .base import BaseObject
from .util import hasnone, allnone

class Item(BaseObject):
    EVENT = ['enter', 'leave', 'timeout', 'removed']

    def __init__(self, name, x, y, create_time, symbol='*', life=None, block=False, hidden=False, debug=False, parent=None) -> None:
        """ Create a new item/tile on the map.
        @param name - the name of this item. 
                      Can be used to remove certain type of tiles on the map.
        @param x - current x position of the item
        @param y - current y position of the item
        @param create_time - timestamp of when this item is created
        @param symbol - what to show on the map
        @param life - how long will this item exists. 
                      Once its life ends, the item will be removed automatically.
        @param block - whether this item should block user's movement.
        @param hidden - whether this item should be shown on the map. 
                        Note that all events are still triggered even if the item is hidden.
        @param debug - whether to print the debugging messages. 
                       (warnings and errors will always be printed)
        """
        super().__init__(debug)

        self.name = name           # name of this item
        self.x = x                 # current position of the item
        self.y = y                 # current position of the item
        self.created = create_time # when was this item created
        self.life = life           # how long will this item exists
        self.symbol = symbol       # what to show on the map
        self.block = block         # whether to block user's movement
        self.hidden = hidden       # whether to show on the map
        self.parent = parent       # which game did this item come from

        self.istouched = False

        self._callback = {e: [] for e in self.EVENT}
        self._timer = {}
    
    def position(self) -> list:
        """ Get current position of this item. """
        return [self.x, self.y]
    
    def show(self, flag: bool = True) -> None:
        """ Set whether the item should be shown in the map or not.
        Note that all events are still triggered even if the item is hidden.
        """
        self.hidden = not flag
        self.log(f'Item-{self.name}: set hidden to {self.hidden!r}')
        return

    def set_block(self, flag: bool = True) -> None:
        """ Set whether the item should block user or not """
        self.block = flag
        self.log(f'Item-{self.name}: set block to {self.block!r}')
        return
    
    ### ------ EVENT FUNCTIONALITIES ------ ###
    
    def fire(self, event: str, *args) -> bool:
        """ Fire a certain event.
        @return whether the event is successfully fired.
        """
        if event not in self.EVENT:
            self.log(f'Item-{self.name}: event {event!r} doesn\'t exist. Event not fired', 'warn')
            return False

        self.log(f'Item-{self.name}: fire {event!r} event')
        if event == 'timeout':
            self._timer[args[0]][1](self)
            del self._timer[args[0]]
        elif event == 'enter':
            self.istouched = True
        elif event == 'leave':
            self.istouched = False

        for cb in self._callback[event]:
            cb(self)
        return True
    
    def subscribe(self, event: str, callback: Callable) -> bool:
        """ Subscribe to an event on this item. 
        The callback will be triggered once the event is fired.
        @return whether the callback is successfully subscribed.
        """
        if event not in self.EVENT:
            self.log(f'Item-{self.name}: event {event!r} not allowed. Event not registered', 'warn')
            self.log(f'Item-{self.name}: Available events: {self.EVENT}', 'warn')
            return False
        
        self._callback[event].append(callback)
        self.log(f'Item-{self.name}: callback {callback.__name__!r} subscribes to the event {event!r}')
        return True

    def unsubscribe(self, event: str, callback: Callable) -> bool:
        """ Unsubscribe a certain function from an event of this item.
        @return whether the event is successfully unsubscribed.
        """
        if event not in self.EVENT:
            self.log(f'Item-{self.name}: event {event!r} not found', 'warn')
            return False
        if callback not in self._callback[event]:
            self.log(f'Item-{self.name}: callback {callback.__name__!r} not found', 'warn')
            return False

        self._callback[event].remove(callback)
        self.log(f'Item-{self.name}: callback {callback.__name__!r} removed from the event {event!r}')
        return True
    
    def timer(self, time: int, callback: Callable) -> int:
        """ Set up a timer. The callback will be triggered once the time is out.
        @return an timer id, which can be used to cancel the timer.
        """
        id = random.randint(1000, 10000)
        self._timer[id] = [time, callback]
        self.log(f'Item-{self.name}: timer {id} is added. handler: {callback.__name__!r}')
        return id
    
    def remove_timer(self, id: int) -> bool:
        """ Remove the existing timer.
        @return whether the timer is successfully removed.
        """
        if id not in self._timer:
            self.log(f'Item-{self.name}: timer {id} not found ({self.name})', 'warn')
            return False
        del self._timer[id]
        self.log(f'Item-{self.name}: timer {id} is removed')
        return True
    

    ### ------ UTILITIES ------ ###
    
    def _tik_timer(self) -> None:
        dead = []
        for id, obj in self._timer.items():
            obj[0] -= 1
            self.log(f'Item-{self.name}: timer {id} remain time: {obj[0]}')
            if obj[0] <= 0:
                dead.append(id)
        for id in dead:
            self.fire('timeout', id)

    def _check_alive(self, timestamp) -> bool:
        """ Check for daily update and return its current status. 
        Please do not call this function, or the whole timeline of this item might be broken.
        """
        if self.life and (timestamp > self.created + self.life):
            self.hidden = True
            return False
        self._tik_timer()
        return True


class Engine(BaseObject):
    # available keyboard events
    KB_EVENT = ['press', 'release'] 
    # default events
    DEFAULT_EVENT = ['onstart', 'update_map', 'step_end', 'onend'] 
    # default keymap of movement control
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

    def __init__(self, width, height, 
                 move_function, 
                 init_x = None, init_y = None, 
                 input = None, 
                 pixel_width = 1, 
                 character_char = 'x', 
                 map_renderer = None, 
                 map_filler = ' ',
                 debug = False) -> None:
        """
        @param width - the width of the map
        @param height - the height of the map
        @param move_function - the movement controller `function(action, x, y) -> [x, y]` of the engine. 
                               The return value will be the new position of the character.
        @param init_x - initial position x of the character
        @param init_y - initial position y of the character
        @param input - input mode. [stdin, pynput]
        @param pixel_width - the width of every pixel. Set this if you're using emoji in the map.
        @param character_char - the char used to resemble the character
        @param map_renderer - the default map render function.
        @param map_filler - what to show if there's no item on the map.
        @param debug - whether to print the debug messages. (warnings and errors are always printed)
        """
        super().__init__(debug)

        self.width = width
        self.height = height
        self.move_cb = move_function
        self.input = input

        self.pixel_width = pixel_width
        self.character_char = character_char
        # current position of the character [x, y]
        self.character = [init_x if init_x is not None else int(height/2), 
                          init_y if init_y is not None else int(width/2)]
        self.map_filler = map_filler
        self.map = [[None for _ in range(width)]       # map information
                          for _ in range(height)]
        self.backpack = []                             # small backpack
        self.isend = False                             # whether the game has ended

        self._timestamp = 0
        self._kb_callback = {e: defaultdict(list) for e in self.KB_EVENT}
        self._subscription = {e: [] for e in self.DEFAULT_EVENT}
        self._layer_renderer = {'map': map_renderer or self.default_map_renderer}
        self._timer = {}
        self._pause_event_once = False

        self.layer = 'map'                                 # current presenting layer
        self.renderer = self._layer_renderer[self.layer]   # current renderer
        if not self.input:
            self.input = 'pynput' if PYNPUT_AVAILABLE else 'stdin'
            self.log(f'Autodetect input system: {self.input!r}')
        self.log(f'Input system {self.input!r} is used')

    def start(self) -> int:
        """ Start the game loop. 
        The current timestamp is yielded in real-time, right before rendering the map.  
        The logic loop of the game is:
         1. announce current timestamp (yield)
         2. render the map
         3. listen to any events and handle valid ones
         4. fire `end_step` event
         5. back to (1)
        Note that your code in game loop will be processed in between (1) and (2).
        """
        self.fire('onstart')
        while not self.isend:
            yield self._timestamp 

            # YOUR CODE IN THE LOOP WILL BE PUT RIGHT HERE

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
            self.log(f'blocked by item')
            return
        self.position(x, y)
        self.log(f'move to ({x}, {y})')
        return

    ### ------ MAP FUNCTIONALITIES ------ ###

    def add_layer(self, name: str, renderer: Callable, switch = False, force_update = False) -> None:
        """ Add a new layer in the game.
        @param name - the name of new layer
        @param renderer - the render function of this layer
        @param switch - whether to switch to this layer immediately after it's created
        @param force_update - whether to force the engine render re-render current layer immediately
        """
        if name in self._layer_renderer:
            self.log(f'layer {name!r} already exist. Renderer overridden.', 'warn')
        
        self._layer_renderer[name] = renderer
        self.log(f'layer {name!r} is added with renderer {renderer.__name__!r}')
        if switch or force_update:
            self.layer = name
            self.renderer = renderer
        if force_update:
            self.renderer(self)
        return

    def switch_layer(self, name: str, force_update: bool = False, pause_event_check: bool = True) -> bool:
        """ Change to another layer.
        @param name - the name of target layer
        @param force_update - whether to re-render the map immediately.
        @param pause_event_check - whether to pause the event check immediately after the layer switched.
        @return `true` if the switching is successful.
        """
        if name not in self._layer_renderer:
            self.log(f'layer {name!r} is not avaliable', 'error')
            self.log(f'available layer list: {str(list(self._layer_renderer.keys()))}', 'debug')
            return False
        
        self.layer = name
        self.renderer = self._layer_renderer[name]
        self.log(f'switch to layer {self.layer!r} with renderer {self.renderer.__name__!r}')

        self._pause_event_once = pause_event_check
        if force_update:
            self.renderer(self)
        return True
    
    def default_map_renderer(self, *args) -> None:
        """ The default renderer.  
        If your renderer somehow is broken, try to set Engine.renderer back to this.
        """
        print()
        print(f'time: {self._timestamp:3}')
        print('.', '-' * self.width * self.pixel_width, '.', sep='')
        for i in range(self.height):
            print('|', end='')
            for j in range(self.width):
                symbol = self._get_tile(i, j)
                print(symbol, end='')
            print('|')
        print('\'', '-' * self.width * self.pixel_width, '\'', sep='')
        return

    def update_map(self, items) -> bool:
        """ [ NOT IMPLEMENTED ] Update a selection of tiles at once """
        # [ TODO ]
        raise NotImplementedError

    def add_item(self, name: str, x: int, y: int, symbol: str, block: bool = False, hidden: bool = False, life: int = None) -> Item:
        """ Add an item (tile) on to the map.
        @param name - the name of this item. 
                      Can be used to remove certain type of tiles on the map.
        @param x - current x position of the item
        @param y - current y position of the item
        @param symbol - what to show on the map
        @param block - whether this item should block user's movement.
        @param hidden - whether this item should be shown on the map. 
                        Note that all events are still triggered even if the item is hidden.
        @param life - how long will this item exists. 
                      Once its life ends, the item will be removed automatically.
        @return created `Item` object
        """
        if self._get_length(symbol) > self.pixel_width:
            self.log(f"Item symbol is longer than the pixel width of your map. This may cause some problem during the rendering", 'warn')
        
        if len(symbol) == 0:
            self.log('Symbol is automatically transformed into space', 'warn')
            symbol = ' '

        new_item = Item(name, x, y, self._timestamp, symbol, life, block, hidden, debug=self.debug, parent=self)

        if self.map[x][y] is not None:
            self.log(f'Original item on ({x}, {y}) is replaced', 'warn')
            self._clean_tile(x, y)
        self.map[x][y] = new_item
        self.log(f'Item {name!r} is added to ({x}, {y})')

        return new_item
    
    def remove_item(self, x: int = None, y: int = None, name: str = None) -> bool:
        """ Remove an existing item on the map.
        If only the name is specified, all items with the given name will be removed.
        If only the x and y are specified, the item on the given position will b removed.
        If all x, y, and name are specified, the item will only be removed if it is on (x, y) and has the same name.
        @return `true` if an item is removed.
        """
        if hasnone([x, y]) and not allnone([x, y]):
            self.log(f'(x, y) should be specified at the same time', 'error')
            self.log(f'item {name!r} on ({x}, {y}) not removed.', 'warn')
            return False
        
        if x is not None and name is None:
            self._clean_tile(x, y)
            return True

        if x is not None:
            if not self.map[x][y]:
                self.log(f'item on ({x}, {y}) not found')
                return False
            if self.map[x][y].name == name: 
                return self._clean_tile(x, y)
            self.log(f'item on ({x}, {y}) is not {name!r}')
            return False
        
        flag = False
        for rid, cid, item in self._get_items():
            if item.name == name:
                flag = self._clean_tile(rid, cid) or flag
        return flag
    
    def find_item(self, name: str = None, symbol: str = None, hidden: bool = None, block: bool = None) -> list:
        """ Find existing items that matches all given properties.  
        Available properties: name, symbol, hidden, block.
        @return - a list of matched items
        """
        result = []
        for _, _, item in self._get_items():
            if name is not None and item.name != name:
                continue
            if symbol is not None and item.symbol != symbol:
                continue
            if hidden is not None and item.hidden != hidden:
                continue
            if block is not None and item.block != block:
                continue
            result.append(item)
        return result

    ### ------ EVENT FUNCTIONALITIES ------ ###

    def fire(self, event: str, *args) -> bool:
        """ Fire a certain event.
        @return whether the event is successfully fired.
        """
        if event not in self._subscription:
            self.log(f'event {event!r} not exist. Event not fired', 'warn')
            return False

        self.log(f'event {event!r} is fired')
        for cb in self._subscription[event]:
            cb(self)
        return True

    def add_event(self, name: str) -> bool:
        """ Register a new event onto the engine. 
        After adding the event, you can now subcribe to your custom event through `subscribe` function.
        @return `true` if the event is successfully registered.
        """
        if name in self._subscription:
            self.log(f'event {name!r} already existed. event not added.', 'warn')
            return False
        
        self._subscription[name] = []
        self.log(f'event {name!r} is added')
        return True
    
    def subscribe(self, event: str, callback: Callable) -> bool:
        """ Subscribe a callback to an event on this item. 
        The callback will be triggered once the event is fired.
        @return whether the callback is successfully subscribed.
        """
        if event not in self._subscription:
            self.log(f'Event {event!r} not exists. Callback not subscribed', 'warn')
            self.log(f'Available events: {list(self._subscription.keys())}', 'warn')
            return False
    
        self._subscription[event].append(callback)
        self.log(f'callback {callback.__name__!r} is subscribed to event {event!r}')
        return True

    def unsubscribe(self, event: str, callback: Callable) -> bool:
        """ Unsubscribe a certain function from the given event.
        If the callback has been registered for multiple times, only the first occurence will be removed.
        @return whether the event is successfully unsubscribed.
        """
        if event not in self._subscription:
            self.log(f'event {event!r} not found', 'warn')
            return False
        if callback not in self._subscription[event]:
            self.log(f'callback {callback.__name__!r} not found', 'warn')
            return False

        self._subscription[event].remove(callback)
        self.log(f'callback {callback.__name__!r} is unsubscribed from the event {event!r}')
        return True

    def subscribe_keyboard(self, key: str, event: str, callback: Callable) -> bool:
        """ Subscribe to a certain keyboard event.  
        If stdin is used, the event will be subscribed to the exact string input ('esc' string, rather than `Esc` key);  
        or if pynput is used, the event will be bound to a single keypress (`Esc` key).  
        The key name of special keys be the same as pynput keycode if pynput is used: 
          https://pynput.readthedocs.io/en/stable/keyboard.html?highlight=key#pynput.keyboard.Key
        @return `true` if the callback is successfully subscribed.
        """
        if self.input == 'stdin': # only press is available for stdin
            event = 'press'
        elif key in keyboard.Key._member_names_:
            key = itemgetter(key)(keyboard.Key)
        else:
            key = keyboard.KeyCode.from_char(key)

        if event not in self.KB_EVENT: 
            self.log(f'action {event!r} not allowed. Callback not subscribed', 'warn')
            self.log(f'Available actions: {self.KB_EVENT}', 'warn')
            return False

        self._kb_callback[event][key].append(callback)
        self.log(f'{event!r} event with key {str(key)!r} subscribed')
        return True

    def unsubscribe_keyboard(self, key: str, event: str, callback: Callable) -> bool:
        """ Unsubscribe a certain callback from the event of the given key .
        If the callback has been registered for multiple times, only the first occurence will be removed.
        @return `true` if the callback is successfully unsubscribed.
        """
        if self.input == 'stdin': # only press is available for stdin
            event = 'press'
        elif key in keyboard.Key._member_names_:
            key = itemgetter(key)(keyboard.Key)
        else:
            key = keyboard.KeyCode.from_char(key)

        if event not in self.KB_EVENT: 
            self.log(f'action {event!r} not found', 'warn')
            return False
        if callback not in self._kb_callback[event][key]:
            self.log(f'callback {callback.__name__!r} not found', 'warn')
            return False
        
        self._kb_callback[event][key].remove(callback) # stdin
        self.log(f'{event!r} event with key {str(key)!r} unsubscribed')
        return True

    def timer(self, time: int, callback: Callable) -> int:
        """ Set up a timer. The callback will be triggered once the time is out.
        @return an timer id, which can be used to cancel the timer.
        """
        id = random.randint(1000, 10000)
        self._timer[id] = [time, callback]
        self.log(f'timer {id} is added')
        return id

    def remove_timer(self, id: int) -> bool:
        """ Remove the existing timer.
        @return whether the timer is successfully removed.
        """
        if id not in self._timer:
            self.log(f'timer {id} not found', 'warn')
            return False
        del self._timer[id]
        self.log(f'timer {id} is removed')
        return True
    
    ### ------ UTILITIES ------ ###

    def _next(self) -> int:
        """ Called when a step ends """
        self._timestamp += 1
        self._check_event()
        self._tik_timer()
        self.fire('step_end')
        return self._timestamp
    
    def _cleanup(self) -> bool:
        """ Called after the game ends """
        ## anything to do?
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
                self.log(f'Received event {str(event)!r} (pynput)')
                updated = self._handle_keyboard(event)
        elif self.input == 'stdin':
            event = input('input: ').lower()
            self.log(f'Received input {event!r} (stdin)')
            updated = self._handle_stdin(event)
        else:
            self.log(f'Selected input system {self.input!r} not supported.', 'error')
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
        if self.layer != 'map': return
        if self._pause_event_once:
            self._pause_event_once = False
            return
        
        for rid, cid, item in self._get_items():
            if rid == self.character[0] and cid == self.character[1]:
                item.fire('enter')
            elif item.istouched:
                item.fire('leave')
            
            alive = item._check_alive(self._timestamp)
            if not alive:
                self._clean_tile(rid, cid)
    
    def _tik_timer(self) -> None:
        """ Check existing timers """
        # [TODO-REFACT]
        dead = []
        for id, obj in self._timer.items():
            obj[0] -= 1
            self.log(f'timer {id} remain time: {obj[0]}')
            if obj[0] <= 0:
                obj[1](self)
                dead.append(id)
        for id in dead:
            self.remove_timer(id)
        return
    
    def _get_tile(self, x: int, y: int) -> str:
        """ Get the tile symbol of a certain position """
        item = self.map[x][y]
        if x == self.character[0] and y == self.character[1]:
            symbol = self.character_char
        elif item and not item.hidden:
            symbol = item.symbol
        else:
            symbol = self.map_filler
        
        symbol_width = self._get_length(symbol)
        width = self.pixel_width - symbol_width + 1
        # print(x, y, width)
        return f'{symbol:>{width}}'
    
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
        self.log(f'Item {item.name!r} on ({x}, {y}) is removed')
        return True
    
    def _print_map(self):
        """ Print all objects on the map array. Just for debugging """
        for row in self.map:
            self.log(row)

    @staticmethod
    def _get_length(symbol):
        return sum(str_util.get_width(ord(char)) for char in symbol)