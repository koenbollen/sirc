# [si]rc - utility functions..

import struct
import re

__all__ = [ "unpack", "unint", "unstring", "regex" ]

def unpack( fmt, raw ):
    """Unpack fmt from raw and return the result and the rest."""
    size = struct.calcsize( fmt )
    #if size > len(raw): return None, raw
    result = struct.unpack( fmt, raw[:size] )
    if len(result) == 1:
        result = result[0]
    return result, raw[size:]

def unint( raw ):
    """alias for unpack( "<i", raw )"""
    return unpack( "<i", raw )

def unstring( raw ):
    """Read a string from raw, read until first \0 and also return the rest."""
    try:
        size = raw.index('\0')
    except ValueError:
        return None, raw
    return raw[:size], raw[size+1:]

regex = re.compile(
        r"^(?P<channel>#[\w_-]+)?(?:@(?P<server>[\.\w]+))?!(?P<command>\w+)"
    )



# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
