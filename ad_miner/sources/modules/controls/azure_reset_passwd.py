from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of
from hashlib import md5


@register_control
class azure_reset_passwd(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_passwords"
        self.control_key = "azure_reset_passwd"

        self.title = "Entra ID password reset privileges"
        self.description = "Users with the right to reset users' passwords"
        self.risk = "These users can change the passwords of other users without knowing their previous password which leads to a control of the account."
        self.poa = "Review the privileged users and ensure they are legitimate."

        self.azure_reset_passwd = requests_results["azure_reset_passwd"]

    def run(self):
        if self.azure_reset_passwd is None:
            self.azure_reset_passwd = []

        page = Page(
            self.arguments.cache_prefix,
            "azure_reset_passwd",
            "Entra ID users with passwords reset privilege",
            self.get_dico_description(),
        )
        grid = Grid("Entra ID users with passwords reset privilege")

        self.reset_passwd = {}
        for path in self.azure_reset_passwd:
            try:
                self.reset_passwd[path.nodes[0].name].append(path.nodes[-1].name)
            except KeyError:
                self.reset_passwd[path.nodes[0].name] = [path.nodes[-1].name]

        data = []
        for user in self.reset_passwd.keys():
            count = len(self.reset_passwd[user])
            hash = md5(user.encode()).hexdigest()
            sortClass = str(count).zfill(6)

            subpage = Page(
                self.arguments.cache_prefix,
                f"passwords_reset_{hash}",
                f"Users which passwords can be reset by {user}",
                self.get_dico_description(),
            )
            subgrid = Grid(f"Users which passwords can be reset by {user}")
            subgrid.setheaders([user])
            subgrid.setData([{user: target} for target in self.reset_passwd[user]])
            subpage.addComponent(subgrid)
            subpage.render()

            data.append(
                {
                    "Privileged user": '<i class="bi bi-person-fill"></i>' + user,
                    "Passwords that can be reset": grid_data_stringify(
                        {
                            "link": f"passwords_reset_{hash}.html",
                            "value": f"{count} password{'s' if count > 1 else ''}",
                            "before_link": f"<i class='bi bi-key-fill {sortClass}' aria-hidden='true'></i>",
                        }
                    ),
                }
            )

        grid.setheaders(["Privileged user", "Passwords that can be reset"])
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.reset_passwd.keys())
        self.name_description = (
            f"{len(self.reset_passwd.keys())} users can reset Entra ID password"
        )

    def get_rating(self) -> int:
        return presence_of(self.reset_passwd.keys(), 2)
