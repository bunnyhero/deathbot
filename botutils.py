# botutils.py

def minutes_string(n):
    return plural_string("minute", n)

def plural_string(root, n):
    n = int(n)
    return "%d %s%s" % (n, root, "" if n == 1 else "s")

def format_timedelta(t):
    """ formats timedelta into a friendly string """
    hours, remainder = divmod(t.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    s = []
    if hours > 0:
        s.append(plural_string("hour", hours))
    if minutes > 0:
        s.append(plural_string("minute", minutes))
    if seconds > 0:
        s.append(plural_string("second", seconds))

    return ", ".join(s)
