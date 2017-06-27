import cherrypy
from dogpile.cache import make_region, register_backend
from dogpile.cache.backends.memory import MemoryBackend


class CherrypyRequestBackend(MemoryBackend):
    """
    A memory backed cache for individual CherryPy requests.

    This provides a cache backend for dogpile.cache which is designed
    to work in a thread-safe manner using cherrypy.request, a thread local
    storage that only lasts for the duration of a request.
    """
    def __init__(self, arguments):
        pass

    @property
    def _cache(self):
        if not hasattr(cherrypy.request, '_girderCache'):
            setattr(cherrypy.request, '_girderCache', {})

        return cherrypy.request._girderCache


register_backend('cherrypy_request', 'girder.utility.cache', 'CherrypyRequestBackend')

cache = make_region(name='girder.cache')
requestCache = make_region(name='girder.request')
