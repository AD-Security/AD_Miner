#!/usr/bin/env python3

# Built-in imports
import json
import shutil
from pathlib import Path
import time
import traceback
import signal
import sys
import subprocess
import requests
from importlib.metadata import version, PackageNotFoundError

# Local library imports
from ad_miner.sources.modules import logger, utils, generic_formating, main_page
from ad_miner.sources.modules.neo4j_class import Neo4j, pre_request
from ad_miner.sources.modules import controls
from ad_miner.sources.modules.common_analysis import (
    rating_color,
    generateDomainMapTrust,
    genNumberOfDCPage,
    genUsersListPage,
    genAllGroupsPage,
    generateComputersListPage,
    generateADCSListPage,
    genAzureTenants,
    genAzureUsers,
    genAzureAdmin,
    genAzureGroups,
    genAzureVM,
    genAzureDevices,
    genAzureApps,
)

# Third party library imports


# Constants
SOURCES_DIRECTORY = Path(__file__).parent / "sources"


# Catch ctrl-c correctly
def handler(signum, frame):
    logger.print_error("Ctrl-c pressed. Exiting...")
    exit(1)


signal.signal(signal.SIGINT, handler)


# Do all the requests (if cached, retrieve from cache, else store in cache)
def populate_data_and_cache(neo4j: Neo4j) -> dict:
    """Populate data and cache it based on configuration settings.

    This function reads a configuration file (config.json) and determines
    whether to execute specific requests or skip them based on the configuration.

    Args:
        neo4j (Neo4j): An instance of the Neo4j class.

    Returns:
        None: This function does not return any values.

    Raises:
        FileNotFoundError: If the config.json file is not found.
        json.JSONDecodeError: If there is an issue parsing the JSON in config.json.
    """

    config_file_path = SOURCES_DIRECTORY / "modules" / "config.json"

    try:
        with config_file_path.open("r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)["requests"]
    except (FileNotFoundError, json.JSONDecodeError) as error:
        logger.print_error(f"Error while parsing {config_file_path}: {error}")

    nb_requests = len(neo4j.all_requests.keys())
    requests_count = 0

    for request_key in neo4j.all_requests.keys():
        requests_count = requests_count + 1
        print(f"[{requests_count}/{nb_requests}] ", end="")
        req = neo4j.all_requests[request_key]
        if not config_data.get(request_key) or config_data[request_key] == "true":
            try:
                neo4j.process_request(neo4j, request_key)
            except Exception as error:  # FIXME specify exception
                logger.print_error(error)
                logger.print_error(traceback.format_exc())

        else:
            req["result"] = None
            logger.print_warning("Skipping request : %s    (config.json)" % request_key)

    logger.print_success("Requests finished !")

    requests_results = {}
    for request_key, value in neo4j.all_requests.items():
        try:
            requests_results[request_key] = value["result"]
        except KeyError:
            logger.print_error(
                f"No result found for request {request_key}. Trying to generate incomplete report."
            )

    neo4j.compute_common_cache(requests_results)

    return requests_results


def prepare_render(arguments) -> None:
    """Prepares the render folder by copying necessary assets.

    Args:
        arguments: Parsed command line arguments.
    """

    folder_name = Path(f"render_{arguments.cache_prefix}")

    if folder_name.exists():
        shutil.rmtree(folder_name)

    folder_name.mkdir(parents=True, exist_ok=True)
    (folder_name / "csv").mkdir()
    (folder_name / "html").mkdir()

    # Create redirect index.html
    (folder_name / "index.html").write_text(
        "<script>window.location.href = './html/index.html'</script>"
    )

    # Copy assets
    subpaths = {
        "css": SOURCES_DIRECTORY / "html" / "bootstrap" / "css",
        "js": SOURCES_DIRECTORY / "html" / "bootstrap" / "js",
        "icons": SOURCES_DIRECTORY / "html" / "bootstrap" / "icons",
        "assets": SOURCES_DIRECTORY / "html" / "assets",
    }

    for sub, src_path in subpaths.items():
        shutil.copytree(src_path, folder_name / sub)

    for js_file in (SOURCES_DIRECTORY / "js").iterdir():
        shutil.copy2(js_file, folder_name / "js")


def get_version_and_commit():
    # Either using pip(x) you get the version number or in dev environment the git commit
    try:
        ver = version("ad-miner")
    except PackageNotFoundError:
        ver = "unknown"

    commit = ""
    try:
        root = Path(__file__).resolve().parent
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    return ver, commit


def get_last_version():
    try:
        r = requests.get("https://www.ad-miner.com/version.json", timeout=0.5)
        data = r.json()
        return data["lastversion"]
    except Exception:
        return "unreachable"


def check_version(lastversion, currentversion):
    try:
        last = tuple(map(int, lastversion.lstrip("v").split(".")))
        current = tuple(map(int, currentversion.lstrip("v").split(".")))

        if last > current:
            logger.print_error(f"New AD Miner version {lastversion} available.")
            logger.print_error(
                "Update with pipx or manually on https://github.com/AD-Security/AD_Miner"
            )
            return
    except Exception:
        return


def main() -> None:
    """Main execution function for the script."""
    start = time.time()
    arguments = utils.args()
    cache_check = utils.cache_check(f"{arguments.cache_prefix}_*", arguments.cache)

    if cache_check["nb_cache"] > 0:
        logger.print_warning(cache_check["message"])

    if arguments.cluster:
        main_server = arguments.bolt.replace("bolt://", "")
        if main_server not in arguments.cluster:
            error_message = (
                f"The main server (-b {arguments.bolt}) should be "
                f"part of the cluster you specified (--cluster {arguments.cluster})."
            )
            logger.print_error(error_message)
            return

    prepare_render(arguments)

    AD_miner_version, AD_miner_commit = get_version_and_commit()
    arguments.version = AD_miner_version
    arguments.commit = AD_miner_commit

    check_version(get_last_version(), AD_miner_version)

    neo4j_version, extract_date, total_objects, number_relations, boolean_azure = pre_request(
        arguments
    )
    arguments.boolean_azure = boolean_azure
    version = neo4j_version.get('version')
    logger.print_success("Your neo4j database uses neo4j version " + version)

    if not version.startswith('4.4.'):
        logger.print_error(
            "Your neo4j database version must be 4.4.X in order to fully use AD Miner"
        )
        sys.exit(-1)

    number_objects = sum([type_label["number_type"] for type_label in total_objects])

    if number_objects == 0:
        logger.print_error(
            "Empty neo4j database : you need to collect data with Sharphound (https://github.com/BloodHoundAD/SharpHound), BloodHound.py (https://github.com/dirkjanm/BloodHound.py) or RustHound (https://github.com/NH-RED-TEAM/RustHound)"
        )
        logger.print_error(
            "And then you can fill your neo4j database with Bloodhound (https://github.com/BloodHoundAD/BloodHound)"
        )
        sys.exit(-1)

    string_information_database = ""

    for type_label in total_objects:
        type_label_2 = generic_formating.clean_label(type_label["labels(x)"])

        if type_label_2 != "":
            string_information_database += (
                f"{type_label_2} : {type_label['number_type']} | "
            )

    string_information_database += f"Relations : {number_relations}"
    logger.print_magenta(string_information_database)

    if arguments.extract_date:
        extract_date = arguments.extract_date
    arguments.extract_date = extract_date

    neo4j = Neo4j(arguments, extract_date, boolean_azure)

    if arguments.cluster:
        neo4j.verify_integrity(neo4j)

    requests_results = populate_data_and_cache(neo4j)

    # Define legacy dicts
    dico_name_description = {}

    data_rating: dict[str, dict[int, list]] = {}
    data_rating["on_premise"] = {
        1: [],  # immediate risk
        2: [],
        3: [],
        4: [],  # handled risk
        5: [],
        -1: [],  # -1 = not tested/disabled, 5 = tested and 0 matching
    }
    data_rating["azure"] = {
        1: [],  # immediate risk
        2: [],
        3: [],
        4: [],  # handled risk
        5: [],
        -1: [],  # -1 = not tested/disabled, 5 = tested and 0 matching
    }
    dico_data = {}
    dico_data["value"] = {}

    dico_category: dict[str, list[str]] = {
        "passwords": [],
        "kerberos": [],
        "permissions": [],
        "misc": [],
        "az_permissions": [],
        "az_passwords": [],
        "az_misc": [],
        "ms_graph": [],
    }

    DESCRIPTION_MAP: dict[str, dict[str, str]] = {}

    # Generate general pages: map trusts, users, computers, dc

    generateDomainMapTrust(requests_results, arguments)
    genNumberOfDCPage(requests_results, arguments)
    genUsersListPage(requests_results, arguments)
    genAllGroupsPage(requests_results, arguments)
    generateComputersListPage(requests_results, arguments)
    generateADCSListPage(requests_results, arguments)
    genAzureTenants(requests_results, arguments)
    genAzureUsers(requests_results, arguments)
    genAzureAdmin(requests_results, arguments)
    genAzureGroups(requests_results, arguments)
    genAzureVM(requests_results, arguments)
    genAzureDevices(requests_results, arguments)
    genAzureApps(requests_results, arguments)

    # Run controls, generate secondary pages, and populate legacy dicts
    for c in controls.control_list:
        t_start = time.time()
        try:
            control = c(arguments, requests_results)
            logger.print_debug(str("Generating control " + control.control_key))
            control.run()

            dico_category[control.category].append(control.control_key)

            DESCRIPTION_MAP[control.control_key] = {
                "title": control.title,
                "description": control.description,
                "interpretation": control.interpretation,
                "risk": control.risk,
                "poa": control.poa,
            }

            dico_name_description[control.control_key] = control.name_description

            data_rating[control.azure_or_onprem][control.get_rating()].append(
                control.control_key
            )

            dico_data["value"][control.control_key] = control.data

            d = round(time.time() - t_start, 2)
            logger.print_warning(str("Done in " + str(d) + "s"))
        except Exception as e:
            logger.print_error("Error while running the following control: ")
            logger.print_error(control.control_key)
            logger.print_error(e)
            logger.print_error(traceback.format_exc())

            try:
                dico_category[control.category].append(control.control_key)
                dico_name_description[control.control_key] = (
                    f"{control.title} analysis failed (control crashed)."
                )
                data_rating[control.azure_or_onprem][-1].append(control.control_key)
                DESCRIPTION_MAP[control.control_key] = {
                    "title": control.title,
                    "description": control.description,
                    "interpretation": control.interpretation,
                    "risk": control.risk,
                    "poa": control.poa,
                }
            except Exception as e:
                logger.print_error("Error while trying to add the control as disabled.")
                logger.print_error(e)
                logger.print_error(traceback.format_exc())

    dico_rating_color = rating_color(data_rating)

    main_page.render(
        arguments,
        requests_results,
        dico_data,
        data_rating,
        dico_name_description,
        dico_rating_color,
        dico_category,
        DESCRIPTION_MAP,
    )
    neo4j.close()

    logger.print_success(
        f"{utils.timer_format(time.time() - start)}! Program finished. Report generated in render_{arguments.cache_prefix}"
    )


if __name__ == "__main__":
    main()
