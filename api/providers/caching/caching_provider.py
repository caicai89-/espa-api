from api.providers.caching import CachingProviderInterfaceV0

import memcache


class CachingProviderException(Exception):
    pass


class CachingProvider(CachingProviderInterfaceV0):

    def __init__(self, timeout=600, debug=0):
        self.cache = memcache.Client(['127.0.0.1:11211'], debug=debug)
        self.timeout = timeout  # seconds

    def get(self, cache_key):
        return self.cache.get(cache_key)

    def set(self, cache_key, value, expirey=None):
        timeout = expirey or self.timeout
        success = self.cache.set(cache_key, value, timeout)
        if not success:
            return False
        return True

    def get_multi(self, cache_keys):
        if not isinstance(cache_keys, list):
            raise TypeError('Cached get multiple keys must list keys')
        return self.cache.get_multi(cache_keys)

    def set_multi(self, cache_dict, expirey=None):
        timeout = expirey or self.timeout
        if not isinstance(cache_dict, dict):
            raise TypeError('Cache set multiple must be dict (key/value) pairs')
        failures = self.cache.set_multi(cache_dict, timeout)
        if failures:
            return False
        return True
