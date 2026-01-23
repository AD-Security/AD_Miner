from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of
from ad_miner.sources.modules.common_analysis import createGraphPage

from hashlib import md5


@register_control
class azure_roles(Control):  # TODO change the class name
    "Docstring of my control"  # TODO small documentation here

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_permissions"
        self.control_key = "azure_roles"

        self.title = "Access to privileged Entra ID roles"
        self.description = "Paths to all builtin and custom Entra ID roles"
        self.risk = "Entra ID roles usually grant privileges on the tenant, it is therefore important to ensure that all accounts with privileged roles are justified to have so."
        self.poa = "Review all the Entra ID roles and the users that have them."

        self.azure_role_listing = requests_results["azure_role_listing"]
        self.azure_role_paths = requests_results["azure_role_paths"]

    def run(self):
        if self.azure_role_listing is None:
            self.azure_role_listing = []

        # Add all paths tot the corresponding role
        paths = {}
        for path in self.azure_role_paths:
            try:
                paths[path.nodes[-1].name].append(path)
            except KeyError:
                paths[path.nodes[-1].name] = [path]

        page = Page(
            self.arguments.cache_prefix,
            "azure_roles",
            "Entra ID roles",
            self.get_dico_description(),
        )
        grid = Grid("Entra ID roles")

        data = []
        self.azure_roles_entry_nodes = []
        for role in self.azure_role_listing:
            if paths.get(role["Name"]):
                # Generate graph page for roles with paths
                hash = md5(role["Name"].encode()).hexdigest()
                createGraphPage(
                    self.arguments.cache_prefix,
                    f"azure_roles_paths_{hash}",
                    "Paths to Entra ID roles",
                    self.get_dico_description(),
                    paths[role["Name"]],
                    self.requests_results,
                )
                # Count the number of nodes that have acces to the role
                unique_nodes = set([path.nodes[0].name for path in paths[role["Name"]]])
                count = len(unique_nodes)
                self.azure_roles_entry_nodes += unique_nodes
                sortClass = str(count).zfill(6)
                data.append(
                    {
                        "Name": '<i class="bi bi-person-bounding-box"></i>' + role["Name"],
                        "Description": role["Description"],
                        "Access to role": grid_data_stringify(
                            {
                                "link": f"azure_roles_paths_{hash}.html",
                                "value": f"{count} account{'s' if count > 1 else ''}",
                                "before_link": f"<i class='bi bi-sign-turn-right {sortClass}' aria-hidden='true'></i>",
                            }
                        ),
                    }
                )
        self.azure_roles_entry_nodes = set(self.azure_roles_entry_nodes)
        grid.setheaders(["Name", "Description", "Access to role"])

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_roles_entry_nodes)
        self.name_description = (
            f"{len(self.azure_roles_entry_nodes)} users have access to Entra ID roles"
        )

    def get_rating(self) -> int:
        return presence_of(self.azure_roles_entry_nodes, 2)
