from ad_miner.sources.modules.utils import HTML_DIRECTORY


class Graph:
    def __init__(self, template="graph", path_limit=80000):
        self.template_base_path = HTML_DIRECTORY / "components/graph/"
        self.template = template
        self.paths = []
        self.nodes = {}
        self.relations = []
        self.relations_hashes = {}
        self.path_limit = path_limit
        self.ghost_computer = {}
        self.ghost_user = {}
        self.dc_computer = {}
        self.user_da = {}
        self.group_da = {}
        self.enabled_users = {}
        self.kerberoastable_users = {}
        self.disabled_users_dict = {}

    def addPath(self, path):
        self.paths.append(path)

    def setPaths(self, paths):
        self.paths = paths

    def addGhostComputers(self, ghost_computer):
        self.ghost_computer = ghost_computer

    def addGhostUsers(self, ghost_user):
        self.ghost_user = ghost_user

    def addDCComputers(self, dc_computer):
        self.dc_computer = dc_computer

    def addUserDA(self, user_da):
        self.user_da = user_da

    def addGroupDA(self, group_da):
        self.group_da = group_da

    def addDisabledUsers(self, disabled_users):
        self.disabled_users_dict = disabled_users

    def addKerberoastableUsers(self, kerberoastable_users):
        self.kerberoastable_users = kerberoastable_users

    def render(self, page_f):

        # Write header
        with open(
            self.template_base_path / (self.template + "_header.html"), "r"
        ) as header_f:
            html_header = header_f.read()
            page_f.write(html_header)

        for index, path in enumerate(self.paths):
            for i in range(len(path.nodes)):

                node = path.nodes[i]

                # Compute node style
                if i == 0:
                    node_position = "start"
                elif i == len(path.nodes) - 1:
                    node_position = "end"
                else:
                    node_position = "intermediate"

                # Add new labels here. A corresponding svg icon should be defined
                # dico_icon in the icon.js file.
                list_labels = [
                    "User",
                    "Foreignsecurityprincipal",
                    "GPO",
                    "Computer",
                    "OU",
                    "Group",
                    "Domain",
                    "Container",
                    "AZDevice",
                    "AZTenant",
                    "AZRole",
                    "ADLocalGroup",
                    "AZApp",
                    "CertTemplate",
                    "RootCA",
                    "EnterpriseCA",
                    "AIACA",
                    "NTAuthStore",
                    "AZServicePrincipal",
                ]

                if node.labels in list_labels:
                    label_instance = node.labels
                elif path.nodes[i].labels[2:] in list_labels:
                    label_instance = node.labels[2:]
                else:
                    label_instance = "Unknown"

                node_attributes = []

                # Add DA icon if node is DC, DA or Domain
                if (
                    (
                        label_instance == "Computer"
                        and self.dc_computer.get(node.name, False)
                    )
                    or (label_instance == "User" and self.user_da.get(node.name, False))
                    or (
                        label_instance == "Group"
                        and self.group_da.get(node.name, False)
                    )
                    or label_instance == "Domain"
                ):
                    node_attributes.append("da")

                # Add ghost icon if ghost
                if (
                    label_instance == "User" and self.ghost_user.get(node.name, False)
                ) or (
                    label_instance == "Computer"
                    and self.ghost_computer.get(node.name, False)
                ):
                    node_attributes.append("ghost")

                if label_instance == "User" and self.disabled_users_dict.get(
                    node.name, False
                ):
                    node_attributes.append("disabled")

                if label_instance == "User" and self.kerberoastable_users.get(
                    node.name, False
                ):
                    node_attributes.append("kerberoastable")

                # New nodes attributes that should be added to the node icon
                # should be added here to the node_attributes list.
                # A corresponding svg icon should the be added to the
                # dico_icon in icon.js

                if not self.nodes.get(path.nodes[i].id):

                    final_graph_node = {
                        "id": path.nodes[i].id,
                        "label": path.nodes[i].name,
                        "domain": path.nodes[i].domain,
                        "shape": "image",
                        "instance": label_instance,
                        "position": node_position,
                        "attributes": node_attributes,
                    }
                    self.nodes[path.nodes[i].id] = final_graph_node
                elif self.nodes[path.nodes[i].id]["position"] == "intermediate" and (
                    node_position == "end" or node_position == "start"
                ):
                    self.nodes[path.nodes[i].id]["position"] = node_position

                if i != 0:
                    relation = {
                        "from": path.nodes[i - 1].id,
                        "to": path.nodes[i].id,
                        "label": path.nodes[i - 1].relation_type,
                    }

                    # Avoid relation duplicated to keep graph clean
                    # Use hashes list for better performance
                    hash_rel = hash(
                        str(relation["from"])
                        + str(relation["to"])
                        + str(relation["label"])
                    )
                    if not self.relations_hashes.get(hash_rel):
                        self.relations.append(relation)
                        self.relations_hashes[hash_rel] = True

        nodes = list(self.nodes.values())
        for n in nodes:  # Sanitize None values (otherwise it creates a bug in JS)
            if n["label"] == None:
                n["label"] = "???"
        page_f.write(f'<script type="text/javascript">window.data_nodes = {nodes};\n')
        page_f.write(f"window.data_edges = {self.relations};</script>\n")
