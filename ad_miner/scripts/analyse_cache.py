import sys
from pathlib import Path

try:
    from ad_miner.sources.modules.cache_security import load_cache_entry
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from ad_miner.sources.modules.cache_security import load_cache_entry

# Constants
MODULES_DIRECTORY = Path(__file__).parent / 'sources/modules'


def request_a():
    module_name = sys.argv[1]
    return retrieveCacheEntry(full_module_path=MODULES_DIRECTORY / module_name)


def retrieveCacheEntry(full_module_path: Path):
    with open(full_module_path, "rb") as f:
        return load_cache_entry(f)


list_path = request_a()

dico_node_rel_node = {}

liste_totale = []

for path in list_path:

    for i in path.nodes:
        liste_totale += [(i.id, i.labels, i.name, i.relation_type)]

print(liste_totale, len(liste_totale))
