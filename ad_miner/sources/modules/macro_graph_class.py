from ad_miner.sources.modules.common_analysis import createGraphPage
from hashlib import md5


class MacroGraphPage:
    def __init__(self):
        self.baseName = ''
        self.paths_dict = {}
        for i in range(256):
            hex_str = f"{i:02x}"
            self.paths_dict[hex_str] = []

    def addPathsAndGetLink(self, baseName, paths_list):
        # To use with list of paths having the same starting point
        key = getKeyFromID(paths_list[0].nodes[0].id)

        self.paths_dict[key] += paths_list
        self.baseName = baseName

        return baseName + '_' + key + '.html'

    def addPathsInBulk(self, baseName, paths_list):
        # Can be used with paths from different starting points
        self.baseName = baseName

        for path in paths_list:
            key = getKeyFromID(path.nodes[0].id)
            self.paths_dict[key].append(path)

    def render_pages(self, arguments, requests_results, dico_description, title):
        for i in range(256):
            hex_str = f"{i:02x}"

            createGraphPage(
                arguments.cache_prefix,
                self.baseName + '_' + hex_str,
                title,
                dico_description,
                self.paths_dict[hex_str],
                requests_results,
                )


def getKeyFromID(id):
    return str(md5(str(id).encode()).hexdigest())[0:2]
