import pickle


class RestrictedCacheUnpickler(pickle.Unpickler):
    ALLOWED_GLOBALS = {
        ("ad_miner.sources.modules.graph_class", "Graph"),
        ("ad_miner.sources.modules.node_neo4j", "Node"),
        ("ad_miner.sources.modules.path_neo4j", "Path"),
        ("builtins", "dict"),
        ("builtins", "frozenset"),
        ("builtins", "list"),
        ("builtins", "set"),
        ("builtins", "slice"),
        ("builtins", "tuple"),
    }

    def find_class(self, module, name):
        if (module, name) in self.ALLOWED_GLOBALS:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"Unsupported cache object: {module}.{name}")


def load_cache_entry(file_obj):
    return RestrictedCacheUnpickler(file_obj).load()
