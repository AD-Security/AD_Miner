from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules import generic_formating, generic_computing
from ad_miner.sources.modules.macro_graph_class import getKeyFromID

from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import (
    get_interest,
)

from urllib.parse import quote
from tqdm import tqdm


@register_control
class my_control_class_name(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "anomaly_acl"

        self.title = "ACL anomalies"
        self.description = "An ACL (Access Control List) is a security mechanism that defines permissions and access rights for objects within the Active Directory structure."
        self.risk = "Misconfigured ACL can create access points or privilege escalation that an attacker could use to compromise the domain.<br /><br /><i class='bi bi-star-fill'></i><i class='bi bi-star-fill'></i><i class='bi bi-star-fill'></i>: At least one domain admin as target<br /><i class='bi bi-star-fill'></i><i class='bi bi-star-fill'></i><i class='bi bi-star'></i>: At least one object has a path to domain admin<br /><i class='bi bi-star-fill'></i><i class='bi bi-star'></i><i class='bi bi-star'></i>: At least one object admin of a computer<br /><i class='bi bi-star'></i><i class='bi bi-star'></i><i class='bi bi-star'></i>: Other"
        self.poa = "Regularly review and clean up ACL entries for users and groups that no longer require them."

        self.anomaly_acl_1 = requests_results["anomaly_acl_1"]
        self.anomaly_acl_2 = requests_results["anomaly_acl_2"]

        self.users_admin_on_computers_count = requests_results["users_admin_on_computers_count"]
        self.dico_is_user_admin_on_computer = requests_results[
            "dico_is_user_admin_on_computer"
        ]
        self.dico_paths_computers_to_DA = requests_results["dico_paths_computers_to_DA"]

        self.admin_list = requests_results["admin_list"]

        self.dico_users_to_da = requests_results["dico_users_to_da"]
        self.dico_computers_to_da = requests_results["dico_computers_to_da"]
        self.dico_groups_to_da = requests_results["dico_groups_to_da"]
        self.dico_ou_to_da = requests_results["dico_ou_to_da"]
        self.dico_gpo_to_da = requests_results["dico_gpo_to_da"]
        self.domains_to_domain_admin = requests_results["domains_to_domain_admin"]

        self.list_computers_admin_computers = requests_results[
            "computers_admin_on_computers"
        ]
        self.computers_admin_to_count = generic_computing.getCountValueFromKey(
            self.list_computers_admin_computers, "source_computer"
        )

        self.unwanted_edges_list = [
            "DelegatedEnrollmentAgent",
            "Enroll",
            "EnrollOnBehalfOf",
            "EnterpriseCAFor",
            "ExtendedByPolicy",
            "GetChanges",
            "GetChangesAll",
            "GetChangesInFilteredSet",
            "HostsCAService",
            "IssuedSignedBy",
            "LocalToComputer",
            "ManageCA",
            "ManageCertificates",
            "MemberOfLocalGroup",
            "NTAuthStoreFor",
            "OIDGroupLink",
            "PublishedTo",
            "RemoteInteractiveLogonPrivilege",
            "RootCAFor",
            "TrustedForNTAuth",
            "WritePKIEnrollmentFlag",
            "WritePKINameFlag",
        ]
        self.unwanted_edges_dico = {e: True for e in self.unwanted_edges_list}

    def run(self):

        if self.anomaly_acl_1 is None and self.anomaly_acl_2 is None:
            page = Page(
                self.arguments.cache_prefix,
                "anomaly_acl",
                "ACL Anomaly ",
                self.get_dico_description(),
            )
            page.render()
            return 0

        for each in range(len(self.anomaly_acl_1)):
            self.anomaly_acl_1[each]["g.members_count"] = "-"

        self.anomaly_acl = self.anomaly_acl_1 + self.anomaly_acl_2

        formated_data_details = []
        formated_data = {}
        anomaly_acl_extract = []
        self.max_interest = 0

        for k in range(len(self.anomaly_acl)):

            label = generic_formating.clean_label(self.anomaly_acl[k]["LABELS(g)"])

            target_label = self.anomaly_acl[k]["labels(n)"]
            target_label = filter(
                lambda x: x != "Base" and x != "AZBase" and x != "Tag_Tier_Zero", target_label
            )
            target_label = list(target_label)  # filter returning generator in python3
            target_label = target_label[0]

            edge_type = self.anomaly_acl[k]["type(r2)"]
            if edge_type in self.unwanted_edges_dico:
                continue

            name_label_instance = f"{self.anomaly_acl[k]['g.name']}{label}{edge_type}"

            if (
                formated_data.get(name_label_instance)
                and formated_data[name_label_instance]["type"]
                == self.anomaly_acl[k]["type(r2)"]
                and formated_data[name_label_instance]["label"] == label
            ):
                formated_data[name_label_instance]["targets"].append(
                    (
                        self.anomaly_acl[k]["n.name"],
                        target_label,
                        self.anomaly_acl[k]["ID(n)"],
                    )
                )
            elif (
                formated_data.get(name_label_instance)
                and formated_data[name_label_instance]["targets"]
                == [self.anomaly_acl[k]["n.name"]]
                and self.anomaly_acl[k]["type(r2)"]
                not in formated_data[name_label_instance]["type"]
                and formated_data[name_label_instance]["label"] == label
            ):
                formated_data[name_label_instance][
                    "type"
                ] += f" | {self.anomaly_acl[k]['type(r2)']}"
            else:
                # it is possible to have an OU and a Group with the same name for example, that's why it is necessary to have the name + the label as key
                formated_data[name_label_instance] = {
                    "name": self.anomaly_acl[k]["g.name"],
                    "label": label,
                    "type": self.anomaly_acl[k]["type(r2)"],
                    "members_count": self.anomaly_acl[k]["g.members_count"],
                    "targets": [
                        (
                            self.anomaly_acl[k]["n.name"],
                            target_label,
                            self.anomaly_acl[k]["ID(n)"],
                        )
                    ],
                }
        for name_label_instance in tqdm(formated_data):
            name_instance = formated_data[name_label_instance]["name"]

            formated_data_details = []
            interest = 0
            for name, target_label, target_id in formated_data[name_label_instance]["targets"]:
                interest = max(
                    get_interest(self.requests_results, target_label, name), interest
                )
                tmp_dict = {}
                paths = []
                tmp_dict["Computers admin"] = "-"
                tmp_dict["Path to DA"] = "-"
                icon = ""

                if target_label == "User":
                    if name in self.admin_list:
                        icon = "bi-gem"
                    else:
                        icon = "bi-person-fill"
                        tmp_dict["targets"] = (
                            '<i class="bi bi-person-fill"></i>' + name
                        )
                    if name in self.dico_is_user_admin_on_computer:
                        count = self.users_admin_on_computers_count[name]
                        tmp_dict["Computers admin"] = grid_data_stringify(
                            {
                                "link": f"users_admin_computers_{getKeyFromID(target_id)}.html?node={target_id}",
                                "value": f"Admin of {count} computer{'s' if count > 1 else ''}",
                                "before_link": f"<i class='bi bi-pc-display-horizontal {str(count).zfill(6)}'></i>",
                            }
                        )
                    if name in self.dico_users_to_da:
                        paths = self.dico_users_to_da[name]

                elif target_label == "Group":
                    icon = "bi-people-fill"

                    if name in self.dico_groups_to_da:
                        paths = self.dico_groups_to_da[name]

                elif target_label == "Computer":
                    icon = "bi-pc-display"

                    if name in self.dico_computers_to_da:
                        paths = self.dico_computers_to_da[name]

                    if name in self.computers_admin_to_count:
                        admin_count = self.computers_admin_to_count[name]
                        sortClass = str(admin_count).zfill(6)
                        tmp_dict["Computers admin"] = grid_data_stringify(
                            {
                                "value": f"{admin_count} computers",
                                "link": f"computer_admin_{quote(str(name))}.html",
                                "before_link": f"<i class='bi bi-pc-display {sortClass}'></i>",
                            }
                        )

                elif target_label == "OU":
                    icon = "bi-building"

                    if name in self.dico_ou_to_da:
                        paths = self.dico_ou_to_da[name]

                elif target_label == "Container":
                    icon = "bi-box"

                elif target_label == "GPO":
                    icon = "bi-journal-text"

                    if name in self.dico_gpo_to_da:
                        paths = self.dico_gpo_to_da[name]

                elif target_label == "CertTemplate":
                    icon = "bi-person-vcard"

                elif target_label == "Domain":
                    icon = "bi-globe"
                    if name in self.domains_to_domain_admin:
                        paths = self.domains_to_domain_admin[name]

                elif target_label == "EnterpriseCA":
                    icon = "bi-house-gear-fill"

                elif target_label == "IssuancePolicy":
                    icon = "bi-card-checklist"

                elif target_label == "AIACA":
                    icon = "bi-textarea"

                elif target_label == "NTAuthStore":
                    icon = "bi-shop-window"

                elif target_label == "RootCA":
                    icon = "bi-building-fill-gear"

                else:
                    print(
                        "Object",
                        target_label,
                        "is unknown by anomaly_acl and will not be analyzed.",
                    )
                count_path_to_DA = len(paths)
                if count_path_to_DA > 0:
                    tmp_dict["Path to DA"] = grid_data_stringify(
                        {
                            "link": f"object_to_domain_admin_{getKeyFromID(target_id)}.html?node={target_id}",
                            "value": f'{count_path_to_DA} path{"s" if count_path_to_DA > 1 else ""} to Domain Admin',
                            "before_link": f"<i class='<i bi bi-sign-turn-right-fill {str(count_path_to_DA).zfill(6)}' style='color:#b00404;'></i>",
                        }
                    )
                tmp_dict["targets"] = f'<i class="bi {icon}"></i>{name}'
                formated_data_details.append(tmp_dict)

            page = Page(
                self.arguments.cache_prefix,
                f"anomaly_acl_details_{name_label_instance.replace(' ', '_')}",
                "Group Anomaly ACL Details",
                self.get_dico_description(),
            )

            grid = Grid("Target Details")

            grid.setheaders(["targets", "Computers admin", "Path to DA"])
            grid.setData(formated_data_details)
            page.addComponent(grid)
            page.render()

            if len(formated_data[name_label_instance]["targets"]) > 1:
                icon = "bi-bullseye"

            # Color for stars
            color = {3: "red", 2: "orange", 1: "yellow"}.get(interest, "green")

            anomaly_acl_extract.append(
                {
                    "name": name_instance,
                    "label": f"{generic_formating.get_label_icon_dictionary()[formated_data[name_label_instance]['label']]} {formated_data[name_label_instance]['label']}",
                    "type": formated_data[name_label_instance]["type"],
                    "members count": (
                        f'<i class="{str(formated_data[name_label_instance]["members_count"]).zfill(6)} bi bi-people-fill"></i>'
                        + str(formated_data[name_label_instance]["members_count"])
                        if formated_data[name_label_instance]["members_count"] != "-"
                        else "-"
                    ),
                    "targets count": grid_data_stringify(
                        {
                            "link": f"anomaly_acl_details_{quote(str(name_label_instance.replace(' ', '_')))}.html",
                            "value": f"{str(len(formated_data[name_label_instance]['targets'])) + ' targets' if len(formated_data[name_label_instance]['targets']) > 1 else formated_data[name_label_instance]['targets'][0][0]}",
                            "before_link": f"<i class='<i bi {icon} {str(len(formated_data[name_label_instance]['targets'])).zfill(6)}'></i>",
                        }
                    ),
                    "interest": f"<span class='{interest}'></span><i class='bi bi-star-fill' style='color: {color}'></i>"
                    * interest
                    + f"<i class='bi bi-star' style='color: {color}'></i>" * (3 - interest),
                }
            )
            self.max_interest = max(interest, self.max_interest)

        page = Page(
            self.arguments.cache_prefix,
            "anomaly_acl",
            "ACL Anomaly",
            self.get_dico_description(),
        )
        grid = Grid("anomaly_acl")
        grid.setheaders(
            ["name", "label", "members count", "type", "targets count", "interest"]
        )

        grid.setData(anomaly_acl_extract)
        page.addComponent(grid)
        page.render()

        self.number_group_ACL_anomaly = len([*formated_data])

        self.data = self.number_group_ACL_anomaly
        self.name_description = (
            f"{self.number_group_ACL_anomaly} groups with potential ACL anomalies"
        )

    def get_rating(self) -> int:
        # -1 = grey, 1 = red, 2 = orange, 3 = yellow, 4 =green, 5 = green,
        interest_to_rating = {0: 5, 1: 3, 2: 2, 3: 1}
        return interest_to_rating[self.max_interest]
