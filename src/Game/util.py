from unicodedata import east_asian_width

def allnone(props):
    try:    it = iter(props)
    except: it = iter([props])
    return all([content == None for content in it])

def hasnone(props):
    try:    it = iter(props)
    except: it = iter([props])
    return any([content == None for content in it])

def pixel_width(string):
    return sum(2 if east_asian_width(char) in 'FNW' else 1 for char in string)