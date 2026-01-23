from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class guest_accounts(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "guest_accounts"

        self.title = "Guest accounts"
        self.description = "List of guest accounts"
        self.risk = "The Guest account allows unauthenticated network users to log in as Guest without a password. These unauthorised users can access all resources accessible to the Guest account on the network. This feature means that any shared objects or folders with permissions that allow access to the Guest account, the Domain Guests group, the Guests group, or the Everyone group are accessible on the network, which can lead to data exposure or corruption."
        self.poa = "Guests accounts should be disabled."

        self.guest_accounts = requests_results["guest_accounts"]

    def run(self):
        page = Page(
            self.arguments.cache_prefix,
            "guest_accounts",
            "Guest accounts",
            self.get_dico_description(),
        )
        grid = Grid("Guest accounts")
        grid.setheaders(["domain", "name", "enabled"])

        # Sort accounts with enabled accounts first
        guest_list = [ude for ude in self.guest_accounts if ude[-1]]
        guest_list += [ude for ude in self.guest_accounts if not ude[-1]]

        data = []
        for account_name, domain, is_enabled in guest_list:
            tmp_data = {"domain": '<i class="bi bi-globe2"></i>' + domain}
            tmp_data["name"] = '<i class="bi bi-person-fill"></i>' + account_name
            tmp_data["enabled"] = (
                '<i class="bi bi-unlock-fill text-danger"></i>Enabled'
                if is_enabled
                else '<i class="bi bi-lock-fill text-success"></i>Disabled'
            )
            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len([ude for ude in self.guest_accounts if ude[-1]])
        self.name_description = f"{self.data} guests accounts are enabled"

    def get_rating(self) -> int:
        return presence_of([ude for ude in self.guest_accounts if ude[-1]])
