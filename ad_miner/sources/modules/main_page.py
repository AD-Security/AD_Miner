import json
import os
from datetime import datetime
from operator import add
from urllib.parse import quote
from numpy import pi, cos, sin, linspace
from random import randint

from ad_miner.sources.modules import common_analysis
from ad_miner.sources.modules.smolcard_class import SmolCard
from ad_miner.sources.modules.utils import TEMPLATES_DIRECTORY


def americanStyle(n: int) -> str:
    """
    Returns the number n with spaces between thousands, e.g. 1234 => 1 234
    """
    return "{:,}".format(n).replace(",", " ")


def getData(arguments, requests_results):
    extract_date = arguments.extract_date

    # Place in this dict all the {{key}} from main_header.html with their respecting value
    data = {}

    # Header
    data["render_name"] = arguments.cache_prefix
    data["date"] = f"{extract_date[-2:]}/{extract_date[-4:-2]}/{extract_date[:4]}"
    data["AD_miner_version"] = arguments.version
    data["AD_miner_commit"] = arguments.commit

    # Stats on the left
    data["nb_domains"] = len(requests_results["domains"])
    data["nb_domain_collected"] = len(requests_results["nb_domain_collected"])

    data["domain_or_domains"] = common_analysis.manage_plural(
        data["nb_domains"], ("domain", "domains")
    )

    data["nb_dc"] = americanStyle(len(requests_results["nb_domain_controllers"]))
    data["nb_da"] = americanStyle(len(requests_results["nb_domain_admins"]))

    data["nb_users"] = americanStyle(len(requests_results["nb_enabled_accounts"]))
    data["nb_groups"] = americanStyle(len(requests_results["nb_groups"]))

    data["nb_computers"] = americanStyle(len(requests_results["nb_computers"]))
    data["nb_adcs"] = americanStyle(len(requests_results["set_is_adcs"]))

    users_computers_count_per_domain = common_analysis.getUserComputersCountPerDomain(
        requests_results
    )

    data["domain_names"] = [k[0] for k in users_computers_count_per_domain]
    data["users_per_domain"] = [k[1] for k in users_computers_count_per_domain]
    data["computers_per_domain"] = [k[2] for k in users_computers_count_per_domain]

    computers_os_obsolete, all_os = common_analysis.manageComputersOs(
        requests_results["os"]
    )

    OS_repartition = sorted(all_os.items(), key=lambda x: x[1], reverse=True)

    data["os_labels"] = [os_rep[0] for os_rep in OS_repartition]
    data["os_repartition"] = [os_rep[1] for os_rep in OS_repartition]

    base_colors = [
        "rgb(255, 123, 0)",
        "rgb(255, 149, 0)",
        "rgb(255, 170, 0)",
        "rgb(255, 195, 0)",
        "rgb(255, 221, 0)",
    ]
    i = 0
    data["os_colors"] = []
    for os_name in data["os_labels"]:
        if os_name in common_analysis.obsolete_os_list:
            data["os_colors"].append("rgb(139, 0, 0)")
        else:
            data["os_colors"].append(base_colors[i])
            i = (i + 1) % len(base_colors)

    data["azure_nb_tenants"] = len(requests_results["azure_tenants"])
    data["azure_nb_users"] = len(requests_results["azure_user"])
    data["azure_nb_admin"] = len(requests_results["azure_admin"])
    data["azure_nb_groups"] = len(requests_results["azure_groups"])
    data["azure_nb_vm"] = len(requests_results["azure_vm"])
    data["azure_nb_apps"] = len(requests_results["azure_apps"])
    data["azure_nb_devices"] = len(requests_results["azure_devices"])

    return data


def get_raw_other_data(arguments):
    try:
        raw_other_list_data = []
        for file_name in os.listdir(arguments.evolution):
            with open(arguments.evolution + "/" + file_name, "r") as f:
                raw_other_list_data.append(json.load(f))
        return raw_other_list_data
    except Exception as e:
        print("Bug Evolution over time 😨 : ", e)
        return None


def complete_data_evolution_time(
    data,
    raw_other_list_data,
    dico_category,
    category_repartition_dict,
    dico_category_invert,
):
    data["label_evolution_time"] = []

    list_immediate_risk = {"on_premise": [], "azure": []}
    list_potential_risk = {"on_premise": [], "azure": []}
    list_minor_risk = {"on_premise": [], "azure": []}
    list_handled_risk = {"on_premise": [], "azure": []}
    list_not_evaluated_risk = {"on_premise": [], "azure": []}

    if raw_other_list_data is not None:

        data["boolean_evolution_over_time"] = "block;"

        dico_data_evolution_time = {
            "nb_domains": [],
            "nb_dc": [],
            "nb_da": [],
            "nb_users": [],
            "nb_groups": [],
            "nb_computers": [],
        }

        # Initialize evolution data for on premise and azure
        for category in dico_category.keys():
            for k in dico_category[category]:
                dico_data_evolution_time[k] = []

        # Initialize evolution data for discontinuated controls ?
        for dico_histo_data in raw_other_list_data:
            for control_key in dico_histo_data["value"].keys():
                dico_data_evolution_time[control_key] = []

        for k in range(len(raw_other_list_data)):

            date_k = raw_other_list_data[k]["datetime"]
            data["label_evolution_time"].append(
                f"{date_k[-4:]}-{date_k[3:5]}-{date_k[:2]}"
            )

            dico_color_category_origin = raw_other_list_data[k]["color_category"]

            dico_color_category = {"on_premise": {}, "azure": {}}

            for key in dico_color_category_origin:
                if key in dico_category_invert:
                    category_repartition = category_repartition_dict[
                        dico_category_invert[key]
                    ]
                    dico_color_category[category_repartition][key] = (
                        dico_color_category_origin[key]
                    )

            value_immediate_risk = {"on_premise": 0, "azure": 0}
            value_potential_risk = {"on_premise": 0, "azure": 0}
            value_minor_risk = {"on_premise": 0, "azure": 0}
            value_handled_risk = {"on_premise": 0, "azure": 0}
            value_not_evaluated_risk = {"on_premise": 0, "azure": 0}

            for name_label in dico_color_category_origin:

                for key in [*dico_category]:
                    for value_instance in range(len(dico_category[key])):
                        if dico_category[key][value_instance] == name_label:
                            category_repartition = category_repartition_dict[key]
                if name_label in dico_color_category[category_repartition]:
                    if dico_color_category[category_repartition][name_label] == "red":
                        value_immediate_risk[category_repartition] += 1
                    elif dico_color_category[category_repartition][name_label] == "orange":
                        value_potential_risk[category_repartition] += 1
                    elif dico_color_category[category_repartition][name_label] == "yellow":
                        value_minor_risk[category_repartition] += 1
                    elif dico_color_category[category_repartition][name_label] == "green":
                        value_handled_risk[category_repartition] += 1
                    elif dico_color_category[category_repartition][name_label] == "grey":
                        value_not_evaluated_risk[category_repartition] += 1

            for category_repartition in ["on_premise", "azure"]:
                list_immediate_risk[category_repartition].append(
                    value_immediate_risk[category_repartition]
                )
                list_potential_risk[category_repartition].append(
                    value_potential_risk[category_repartition]
                )
                list_minor_risk[category_repartition].append(
                    value_minor_risk[category_repartition]
                )
                list_handled_risk[category_repartition].append(
                    value_handled_risk[category_repartition]
                )
                list_not_evaluated_risk[category_repartition].append(
                    value_not_evaluated_risk[category_repartition]
                )

            for key in dico_data_evolution_time:
                if key in [
                    "nb_domains",
                    "nb_dc",
                    "nb_da",
                    "nb_users",
                    "nb_groups",
                    "nb_computers",
                ]:
                    dico_data_evolution_time[key].append(
                        raw_other_list_data[k]["general_statistic"][key]
                    )
                else:
                    if raw_other_list_data[k]["value"].get(key) is not None:
                        dico_data_evolution_time[key].append(
                            raw_other_list_data[k]["value"][key]
                        )
                    else:  # Fill with 0 when no data
                        dico_data_evolution_time[key].append(0)

        data["dico_data_evolution_time"] = dico_data_evolution_time
    else:
        data["boolean_evolution_over_time"] = "none"
        data["dico_data_evolution_time"] = {}

    data["value_evolution_time_immediate_risk"] = (
        list_immediate_risk["on_premise"] + list_immediate_risk["azure"]
    )
    data["value_evolution_time_potential_risk"] = (
        list_potential_risk["on_premise"] + list_potential_risk["azure"]
    )
    data["value_evolution_time_minor_risk"] = (
        list_minor_risk["on_premise"] + list_potential_risk["azure"]
    )
    data["value_evolution_time_handled_risk"] = (
        list_handled_risk["on_premise"] + list_potential_risk["azure"]
    )
    data["value_not_evaluated_time_handled_risk"] = (
        list_not_evaluated_risk["on_premise"] + list_potential_risk["azure"]
    )

    return data


def populate_dico_data(data, dico_data, arguments, requests_results, dico_rating_color):
    """
    This function creates the data dictionary which is saved in json in the client's report
    """
    dico_data["datetime"] = data["date"]
    dico_data["render_name"] = arguments.cache_prefix
    dico_data["AD_miner_version"] = data["AD_miner_version"]
    dico_data["AD_miner_commit"] = data["AD_miner_commit"]
    dico_data["general_statistic"] = {
        "nb_domains": len(requests_results["domains"]),
        "nb_dc": len(requests_results["nb_domain_controllers"]),
        "nb_da": len(requests_results["nb_domain_admins"]),
        "nb_users": len(requests_results["nb_enabled_accounts"]),
        "nb_groups": len(requests_results["nb_groups"]),
        "nb_computers": len(requests_results["nb_computers"]),
        "nb_adcs": len(requests_results["set_is_adcs"]),
    }
    dico_data["azure"] = {
        "azure_nb_tenants": len(requests_results["azure_tenants"]),
        "azure_nb_users": len(requests_results["azure_user"]),
        "azure_nb_admin": len(requests_results["azure_admin"]),
        "azure_nb_groups": len(requests_results["azure_groups"]),
        "azure_nb_vm": len(requests_results["azure_vm"]),
        "azure_nb_apps": len(requests_results["azure_apps"]),
        "azure_nb_devices": len(requests_results["azure_devices"]),
    }
    # dico_data["value"] = {
    #     # On-premise

    #     # Azure
    # }
    dico_data["color_category"] = {
        **dico_rating_color["on_premise"],
        **dico_rating_color["azure"],
    }

    return dico_data


def get_hexagons_pos(
    n_hexagons: int, angle_start: float, angle_end: float
) -> list[list[float]]:
    angle_and_pos = []
    hex_offset_v = -3.5  # Offset to compensate hexagon height
    hex_offset_h = -2.5  # Offset to compensate hexagon width

    # harcoded values of concentric arcs for hexagon placement
    arc_distances = [27.5, 35.3, 43.5]

    n_arcs = len(arc_distances)
    angle = angle_end - angle_start
    arcs_lengths = [angle * arc_distance for arc_distance in arc_distances]
    total_length = sum(arcs_lengths)

    hex_per_arc = [int(n_hexagons * le / total_length) for le in arcs_lengths]
    if sum(hex_per_arc) < n_hexagons:
        hex_per_arc[-2] += 1
    while sum(hex_per_arc) < n_hexagons:
        hex_per_arc[-1] += 1

    for i in range(n_arcs):
        to_place = hex_per_arc[i]
        if to_place == 0:
            continue

        rad = arc_distances[i]
        d_theta = angle / to_place
        angles = [angle_start + (i + 0.5) * d_theta for i in range(to_place)]
        for j in range(to_place):

            left = round(50 + rad * cos(angles[j]) + hex_offset_h, 2)
            top = round(50 - rad * sin(angles[j]) + hex_offset_v, 2)

            current_angle = angles[j] - angle_start
            angle_and_pos.append((current_angle, top, left))

    angle_and_pos.sort(key=lambda x: x[0])

    hex_pos = [(top, left) for angle, top, left in angle_and_pos]

    return hex_pos


def render(
    arguments,
    requests_results,
    dico_data,
    data_rating,
    dico_name_description,
    dico_rating_color,
    dico_category,
    DESCRIPTION_MAP,
):
    dico_category_invert = {}
    for key in dico_category:
        for value in dico_category[key]:
            dico_category_invert[value] = key

    category_repartition_dict = {}
    for k in ["passwords", "kerberos", "permissions", "misc"]:
        category_repartition_dict[k] = "on_premise"
    for k in ["az_permissions", "az_passwords", "az_misc", "ms_graph"]:
        category_repartition_dict[k] = "azure"

    if arguments.evolution != "":
        raw_other_list_data = get_raw_other_data(arguments)
    else:
        raw_other_list_data = None

    data = getData(arguments, requests_results)

    dico_data = populate_dico_data(
        data, dico_data, arguments, requests_results, dico_rating_color
    )

    # dico_rating_color = rating.rating_color(data_rating)

    # dico_data = create_dico_data(
    #     data, arguments, domains, computers, users, objects, azure, dico_rating_color
    # )

    if raw_other_list_data != None:
        raw_other_list_data.append(dico_data)

        raw_other_list_data_2 = []
        list_date_raw_other_list_data = [k["datetime"] for k in raw_other_list_data]
        dates_raw_other_list_data = [
            datetime.strptime(date, "%d/%m/%Y")
            for date in list_date_raw_other_list_data
        ]
        dates_raw_other_list_data.sort()
        dates_raw_other_list_data = [
            datetime.strftime(date, "%d/%m/%Y") for date in dates_raw_other_list_data
        ]
        for date_instance in dates_raw_other_list_data:
            for dico in raw_other_list_data:
                if dico["datetime"] == date_instance:
                    raw_other_list_data_2.append(dico)
                    break
        raw_other_list_data = raw_other_list_data_2

    data = complete_data_evolution_time(
        data,
        raw_other_list_data,
        dico_category,
        category_repartition_dict,
        dico_category_invert,
    )  # for the chart evolution over time

    # dico_name_description = {
    #     # azure
    # }

    descriptions = DESCRIPTION_MAP
    dico_name_title = {k: descriptions[k].get("title") for k in descriptions.keys()}

    data["boolean_azure"] = "flex" if arguments.boolean_azure else "none"

    # On premise
    data["on_premise"] = {}

    data["on_premise"]["immediate_risk"] = len(data_rating["on_premise"][1])
    data["on_premise"]["potential_risk"] = len(data_rating["on_premise"][2])
    data["on_premise"]["minor_risk"] = len(data_rating["on_premise"][3])
    data["on_premise"]["handled_risk"] = len(
        data_rating["on_premise"][4] + data_rating["on_premise"][5]
    )

    data["on_premise"]["immediate_risk_list"] = data_rating["on_premise"][1]
    data["on_premise"]["potential_risk_list"] = data_rating["on_premise"][2]
    data["on_premise"]["minor_risk_list"] = data_rating["on_premise"][3]
    data["on_premise"]["handled_risk_list"] = (
        data_rating["on_premise"][4] + data_rating["on_premise"][5]
    )

    # Azure
    data["azure"] = {}

    data["azure"]["immediate_risk"] = len(data_rating["azure"][1])
    data["azure"]["potential_risk"] = len(data_rating["azure"][2])
    data["azure"]["minor_risk"] = len(data_rating["azure"][3])
    data["azure"]["handled_risk"] = len(
        data_rating["azure"][4] + data_rating["azure"][5]
    )

    data["azure"]["immediate_risk_list"] = data_rating["azure"][1]
    data["azure"]["potential_risk_list"] = data_rating["azure"][2]
    data["azure"]["minor_risk_list"] = data_rating["azure"][3]
    data["azure"]["handled_risk_list"] = (
        data_rating["azure"][4] + data_rating["azure"][5]
    )

    global_risk_controls = {
        "immediate_risk": {
            "code": "D",
            "colors": "245, 75, 75",
            "i_class": "bi bi-exclamation-diamond-fill",
            "div_class": "danger",
            "panel_key": "list_cards_dangerous_issues",
            "risk_name": "Critical",
        },
        "potential_risk": {
            "code": "C",
            "colors": "245, 177, 75",
            "i_class": "bi bi-exclamation-triangle-fill",
            "div_class": "orange",
            "panel_key": "list_cards_alert_issues",
            "risk_name": "Major",
        },
        "minor_risk": {
            "code": "B",
            "colors": "255, 221, 0",
            "i_class": "bi bi-dash-circle-fill",
            "div_class": "yellow",
            "panel_key": "list_cards_minor_alert_issues",
            "risk_name": "Minor",
        },
        "handled_risk": {
            "code": "A",
            "colors": "91, 180, 32",
            "i_class": "bi bi-check-circle-fill",
            "div_class": "success",
            "panel_key": "",
            "risk_name": "",
        },
    }
    data["on_premise"]["permissions_data"] = []
    data["on_premise"]["passwords_data"] = []
    data["on_premise"]["kerberos_data"] = []
    data["on_premise"]["misc_data"] = []

    # azure
    data["azure"]["az_permissions_data"] = []
    data["azure"]["az_passwords_data"] = []
    data["azure"]["az_misc_data"] = []
    data["azure"]["ms_graph_data"] = []

    data["on_premise"]["global_rating"] = ""
    data["azure"]["global_rating"] = ""

    for category_repartition in ["on_premise", "azure"]:
        for risk_control in global_risk_controls:

            if category_repartition == "on_premise":  # on premise
                categories = {
                    "permissions": 0,
                    "passwords": 0,
                    "kerberos": 0,
                    "misc": 0,
                }

                for control in data["on_premise"][f"{risk_control}_list"]:

                    for category in categories.keys():
                        if control in dico_category[category]:
                            categories[category] += 1

            else:  # azure
                categories = {
                    "az_permissions": 0,
                    "az_passwords": 0,
                    "az_misc": 0,
                    "ms_graph": 0,
                }

                for control in data["azure"][f"{risk_control}_list"]:

                    for category in categories.keys():
                        if control in dico_category[category]:
                            categories[category] += 1

            for category in categories:
                if (
                    categories[category] > 0
                    and f"{category}_letter_grade" not in data[category_repartition]
                ):
                    data[category_repartition][f"{category}_letter_grade"] = (
                        global_risk_controls[risk_control]["code"]
                    )
                    data[category_repartition][f"{category}_letter_color"] = (
                        global_risk_controls[risk_control]["colors"]
                    )
                    data[category_repartition][
                        f"{category}_graph_summary"
                    ] = f"""
                        <p><i class="{global_risk_controls[risk_control]["i_class"]}" style="color: rgb({global_risk_controls[risk_control]["colors"]}); margin-right: 3px;"></i>
                            <span>{categories[category]}</span> {global_risk_controls[risk_control]["risk_name"]} {common_analysis.manage_plural(categories[category], ("Vulnerability", "Vulnerabilities"))}
                        </p>"""
                data[category_repartition][f"{category}_data"].append(
                    categories[category]
                )

            # Setting global risk info
            if (
                not data[category_repartition]["global_rating"]
                and data[category_repartition][risk_control] > 0
            ):
                data[category_repartition][
                    "global_rating"
                ] = f"""
                    <div class="alert alert-{global_risk_controls[risk_control]["div_class"]} d-flex align-items-center global-rating" role="alert">
                            <i class="{global_risk_controls[risk_control]["i_class"]} rating-icon"></i>
                            <div class="rating-text">
                            {global_risk_controls[risk_control]["risk_name"].upper()}
                            </div>
                        </div>
                """
                data[category_repartition]["main_letter_grade"] = global_risk_controls[
                    risk_control
                ]["code"]
                data[category_repartition]["main_letter_color"] = global_risk_controls[
                    risk_control
                ]["colors"]

            # Creating cards of the right panel
            if global_risk_controls[risk_control]["panel_key"]:
                data[category_repartition][
                    global_risk_controls[risk_control]["panel_key"]
                ] = ""
                red_status = f"""<i class='{global_risk_controls[risk_control]["i_class"]}' style='color: rgb({global_risk_controls[risk_control]["colors"]}); margin-right: 3px;'></i>{risk_control.replace("_", " ").capitalize()}"""
                for issue in data[category_repartition][f"{risk_control}_list"]:
                    custom_title = dico_name_description[issue].replace("$", "")
                    data[category_repartition][
                        global_risk_controls[risk_control]["panel_key"]
                    ] += f"""
                        <a href="{issue}.html">
                            <div class="card threat-card" custom-title="{custom_title}" custom-status="{red_status}">
                                <div class="card-body">
                                    <h6 class="card-title">{dico_name_title[issue]}</h6>
                                </div>
                                <span class="position-absolute top-0 start-100 translate-middle p-2 border border-light rounded-circle"
                                style="background-color: rgb({global_risk_controls[risk_control]["colors"]});">
                                </span>
                                </div>
                        </a>
                    """

        data[category_repartition]["issue_or_issues"] = common_analysis.manage_plural(
            data[category_repartition]["immediate_risk"], ("issue", "issues")
        )
        data[category_repartition]["vuln_text_major_risk"] = (
            common_analysis.manage_plural(
                data[category_repartition]["potential_risk"],
                ("vulnerability", "vulnerabilities"),
            )
        )
        data[category_repartition]["alert_or_alerts"] = common_analysis.manage_plural(
            data[category_repartition]["potential_risk"], ("Alert", "Alerts")
        )
        data[category_repartition]["minor_alert_or_alerts"] = (
            common_analysis.manage_plural(
                data[category_repartition]["minor_risk"],
                ("Minor issue", "Minor issues"),
            )
        )

    data["on_premise"]["main_graph_data"] = [
        l1 + l2 + l3 + l4
        for l1, l2, l3, l4 in zip(
            data["on_premise"]["permissions_data"],
            data["on_premise"]["kerberos_data"],
            data["on_premise"]["passwords_data"],
            data["on_premise"]["misc_data"],
        )
    ]
    data["azure"]["main_graph_data"] = [
        l1 + l2 + l3 + l4
        for l1, l2, l3, l4 in zip(
            data["azure"]["ms_graph_data"],
            data["azure"]["az_permissions_data"],
            data["azure"]["az_passwords_data"],
            data["azure"]["az_misc_data"],
        )
    ]

    with open("./render_%s/html/index.html" % arguments.cache_prefix, "w") as page_f:
        with (TEMPLATES_DIRECTORY / "main_header.html").open(mode="r") as header_f:
            # This part extracts the {{something}} variables in the html template and replaces them with their value in the getData function
            # Every ` char will be skipped
            original = header_f.read()
            content = ""

            i = 0
            while i < len(original):
                if original[i] == "{" and original[i + 1] == "{":
                    j = 2
                    key = ""
                    while original[i + j] != "}" and original[i + j + 1] != "}":
                        key += original[i + j]
                        j += 1
                    key += original[i + j]
                    try:
                        if "on_premise|" in key:
                            content += str(
                                data["on_premise"][key.split("on_premise|")[1]]
                            )

                        elif "azure|" in key:
                            content += str(data["azure"][key.split("azure|")[1]])
                        else:
                            content += str(data[key])

                    except KeyError:
                        content += "N/A"
                    i += len(key) + 4
                elif original[i] == "`":
                    i += 1
                else:
                    content += original[i]
                    i += 1

            page_f.write(content)

            # secondary = Page(arguments.cache_prefix, "cards", f"{arguments.cache_prefix} - {arguments.extract_date[-2:]}/{arguments.extract_date[-4:-2]}/{arguments.extract_date[:4]}", "Following data provide indicators to measure the cybersecurity risk exposure of your Active Directory infrastructure",include_js=["hide_cards"])
            # descriptions = json.load(open('description.json'))
            # print(rating_dic)
            cardsHtml = ""
            for category_repartition in ["on_premise", "azure"]:
                for k in data_rating[category_repartition].keys():
                    for vuln in data_rating[category_repartition][k]:

                        if descriptions.get(vuln):
                            description = descriptions[vuln]["description"]
                        else:
                            description = vuln

                        cardsHtml += SmolCard(
                            id=vuln,
                            criticity=str(k),
                            href=f"{vuln}.html",
                            description=description,
                            details=dico_name_description.get(vuln),
                            evolution_data=data["dico_data_evolution_time"],
                            evolution_labels=data["label_evolution_time"],
                            category=dico_category_invert[vuln],
                            title=DESCRIPTION_MAP[vuln]["title"],
                        ).render(page_f, return_html=True)

            modal_header = open(
                TEMPLATES_DIRECTORY / "cards_modal_header.html", "r"
            ).read()
            modal_footer = """
                </div>
        </div>
    <div class="modal-footer">
    </div>
    </div>
</div>
</div>
            """
            if arguments.evolution == "":
                modal_footer += """<script>
                document.querySelector('#flexSwitchCheckDefault').setAttribute('disabled', '');
                document.querySelector('#switchLogScaleDiv').style.display = 'none';
                </script>
                """

            page_f.write(modal_header + cardsHtml + modal_footer)
            # html = secondary.returnHtml()

    with open(
        f"./render_{arguments.cache_prefix}/data_{arguments.cache_prefix}_{arguments.extract_date}.json",
        "w",
    ) as f:
        f.write(json.dumps(dico_data, indent=4))

    with open(f"./render_{arguments.cache_prefix}/js/main_circle.js", "a") as f_page:

        dico_js = {}

        angles = {
            "passwords": (-2 * pi / 3, -pi),
            "kerberos": (0, -pi / 3),
            "permissions": (0, pi),
            "misc": (-pi / 3, -2 * pi / 3),
            "az_permissions": (0, pi),
            "az_misc": (-pi / 3, -2 * pi / 3),
            "az_passwords": (-2 * pi / 3, -pi),
            "ms_graph": (0, -pi / 3),
        }

        dico_position = {}

        for category in dico_category:
            number_of_controls = len(dico_category[category])
            dico_position[category] = get_hexagons_pos(
                number_of_controls, angles[category][0], angles[category][1]
            )

        dico_position_instance = {
            "passwords": 0,
            "kerberos": 0,
            "permissions": 0,
            "misc": 0,
            "az_misc": 0,
            "az_permissions": 0,
            "az_passwords": 0,
            "ms_graph": 0,
        }

        controls_by_color = {
            "grey": [],
            "green": [],
            "yellow": [],
            "orange": [],
            "red": [],
        }

        for category in dico_category:
            for indicator in dico_category[category]:

                if dico_rating_color[category_repartition_dict[category]].get(
                    indicator
                ):
                    color = dico_rating_color[category_repartition_dict[category]][
                        indicator
                    ]

                else:
                    color = "grey"

                controls_by_color[color].append((category, indicator))

        for color in controls_by_color.keys():
            for category, indicator in controls_by_color[color]:

                dico_js[indicator] = {
                    "color": color,
                    "name": dico_name_title[indicator],
                    "category_repartition": category_repartition_dict[category],
                    "link": quote(str(indicator)) + ".html",
                    "category": category,
                    "position": dico_position[category][
                        dico_position_instance[category]
                    ],
                    "title": (
                        dico_name_description[indicator].replace("$", "")
                        if dico_name_description.get(indicator)
                        else indicator
                    ),
                }
                dico_position_instance[category] += 1

        string_dico = f"""\n var dico_entry = {json.dumps(dico_js)} \n
    display_all_hexagons(dico_entry);"""
        f_page.write(string_dico)

    return
