from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import MODULES_DIRECTORY


import json


@register_control
class primaryGroupID_lower_than_1000(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "rid_singularities"

        self.title = "Unexpected PrimaryGroupID"
        self.description = "Accounts with either an unknown RID, or RID-name missmatches."
        self.risk = "In Active Directory, the primaryGroupId attribute of a user or machine account implicitly assigns this account to a group, even if this group is not listed in the user's memberOf attribute. Membership of a group via this attribute does not appear in the list of group members in certain interfaces. This attribute can be used to hide an account's membership of a group."
        self.poa = "We recommend that you reset the primaryGroupId attributes of the users or computers concerned to their default values."

        self.primaryGroupID_lower_than_1000 = requests_results["primaryGroupID_lower_than_1000"]

    def run(self):
        if self.primaryGroupID_lower_than_1000 is None:
            self.primaryGroupID_lower_than_1000 = []

        known_RIDs = json.loads((MODULES_DIRECTORY / "known_RIDs.json").read_text(encoding="utf-8"))

        page = Page(
            self.arguments.cache_prefix,
            "rid_singularities",
            "Unexpected accounts with lower than 1000 RIDs",
            self.get_dico_description(),
        )
        grid = Grid("Unexpected accounts with lower than 1000 RIDs")
        grid.setheaders(["domain", "name", "RID", "reason"])

        data = []

        for rid, name, domain, is_da in self.primaryGroupID_lower_than_1000:
            name_without_domain = name.replace("@", "").replace(domain, "")

            tmp_data = {}
            if str(rid) not in known_RIDs:
                tmp_data["domain"] = '<i class="bi bi-globe2"></i>' + domain
                tmp_data["RID"] = str(rid)
                tmp_data["name"] = '<i class="bi bi-gem"></i>' + name if is_da else name
                tmp_data["reason"] = "Unknown RID"
                data.append(tmp_data)
            elif name_without_domain not in known_RIDs[str(rid)]:
                tmp_data["domain"] = '<i class="bi bi-globe2"></i>' + domain
                tmp_data["RID"] = str(rid)
                tmp_data["name"] = '<i class="bi bi-gem"></i>' + name if is_da else name
                tmp_data["reason"] = "Unexpected name, expected : " + known_RIDs[str(rid)][0]
                data.append(tmp_data)

        data = sorted(data, key=lambda x: x["RID"])

        sorted_data = [tmp_data for tmp_data in data if tmp_data["reason"].startswith("Unknown")]
        sorted_data += [tmp_data for tmp_data in data if tmp_data["reason"].startswith("Unexpected")]

        self.rid_singularities = len(sorted_data)

        grid.setData(sorted_data)
        page.addComponent(grid)
        page.render()

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = self.rid_singularities

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.data} accounts with unknown RIDs or unexpected names"

    def get_rating(self) -> int:
        return 2 if self.rid_singularities > 0 else 5
