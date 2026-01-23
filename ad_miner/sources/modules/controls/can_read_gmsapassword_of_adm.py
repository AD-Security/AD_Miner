from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of, createGraphPage

from urllib.parse import quote


@register_control
class can_read_gmsapassword_of_adm(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"

        self.category = "passwords"

        self.control_key = "can_read_gmsapassword_of_adm"

        self.title = "Objects can read GMSA passwords of administrators"
        self.description = "GMSA stands for Group Managed Service Account. GMSAs are a special type of service account that are designed to provide improved security and manageability for service applications. GMSAs have their own passwords that are managed by the Active Directory and automatically rotated, making them more secure than traditional service accounts."
        self.risk = "Being able to read GMSA passwords means that accounts can be fully compromised."
        self.poa = "Review these rights to ensure they are legitimate and useful."

        self.can_read_gmsapassword_of_adm = requests_results[
            "can_read_gmsapassword_of_adm"
        ]

    def run(self):
        if self.can_read_gmsapassword_of_adm is None:
            return
        # page = Page(
        #     self.arguments.cache_prefix,
        #     "can_read_gmsapassword_of_adm",
        #     "Objects allowed to read the GMSA of objects with admincount=True",
        #     "can_read_gmsapassword_of_adm",
        # )
        # grid = Grid("Number of accounts or groups with unexpected SID history")
        # grid.setheaders(["domain", "object_allowed", "object_targeted"])
        # grid.setData(self.can_read_gmsapassword_of_adm)
        # page.addComponent(grid)
        # page.render()
        page = Page(
            self.arguments.cache_prefix,
            "can_read_gmsapassword_of_adm",
            "List of non-privileged users that can read GMSAPassword on privileged accounts",
            self.get_dico_description(),
        )
        # Build raw data from requests
        data = {}
        for path in self.can_read_gmsapassword_of_adm:
            try:
                data[path.nodes[0]]["paths"].append(path)
                if path.nodes[-1].name not in data[path.nodes[0]]["target"]:
                    data[path.nodes[0]]["target"].append(path.nodes[-1].name)
            except KeyError:
                data[path.nodes[0]] = {
                    "domain": path.nodes[0].domain,
                    "name": path.nodes[0].name,
                    "target": [path.nodes[-1].name],
                    "paths": [path],
                }

        # Build grid data
        grid_data = []
        for d in data.values():
            sortClass = str(len(d["paths"])).zfill(6)
            tmp_grid_data = {
                "domain": '<i class="bi bi-globe2"></i>' + d["domain"],
                "name": '<i class="bi bi-person-fill"></i>' + d["name"],
                "target": grid_data_stringify(
                    {
                        "value": f"{len(d['paths'])} paths to {len(d['target'])} target{'s' if len(d['target'])>1 else ''}",
                        "link": f"can_read_gmsapassword_of_adm_from_{quote(str(d['name']))}.html",
                        "before_link": f"<i class='{sortClass} bi bi-sign-turn-right' aria-hidden='true'></i>",
                    }
                ),
            }
            grid_data.append(tmp_grid_data)

            # Build graph data
            createGraphPage(
                self.arguments.cache_prefix,
                f"can_read_gmsapassword_of_adm_from_{d['name']}",
                f"{d['name']} can read GMSA Password attack paths on privileged accounts",
                self.get_dico_description(),
                d["paths"],
                self.requests_results,
            )

        self.can_read_gmsapassword_of_adm = data.keys()
        grid = Grid("Users that can read GMSA Password")
        grid.setheaders(["domain", "name", "target"])
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = (
            len(self.can_read_gmsapassword_of_adm)
            if self.can_read_gmsapassword_of_adm
            else 0
        )

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{len(self.can_read_gmsapassword_of_adm)} can read GMSA passwords of Administrators"

    def get_rating(self) -> int:
        return presence_of(self.can_read_gmsapassword_of_adm)
