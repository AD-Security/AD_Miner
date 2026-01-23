class Path:
    def __init__(self, nodes):
        self.nodes = nodes

    def __eq__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        if len(self.nodes) != len(other.nodes):
            return False

        ret = True
        for i in range(len(self.nodes)):
            ret = ret and (self.nodes[i] == other.nodes[i])
        return ret

    def reverse(self, nodes_cache):
        self.nodes.reverse()
        new_nodes = []
        for i in range(len(self.nodes) - 1):
            node = nodes_cache.get_node(self.nodes[i].id, self.nodes[i].labels, self.nodes[i].name, self.nodes[i].domain, self.nodes[i].tenant_id, self.nodes[i + 1].relation_type)
            new_nodes.append(node)
        node = nodes_cache.get_node(self.nodes[-1].id, self.nodes[-1].labels, self.nodes[-1].name, self.nodes[-1].domain, self.nodes[-1].tenant_id, "")
        new_nodes.append(node)
        self.nodes = new_nodes
