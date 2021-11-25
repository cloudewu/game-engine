
def allnone(props):
    try:    it = iter(props)
    except: it = iter([props])
    return all([content == None for content in it])

def hasnone(props):
    try:    it = iter(props)
    except: it = iter([props])
    return any([content == None for content in it])