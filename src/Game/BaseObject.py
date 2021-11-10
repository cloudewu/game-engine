
class BaseObject(object):
    def __init__(self, debug = False):
        super().__init__()

        self.debug = debug

    def log(self, message, level='debug') -> str:
        if level.lower() == 'debug' and not self.debug: return

        message = f'[ {level.upper()} ] {message}'
        print(message)
        return message