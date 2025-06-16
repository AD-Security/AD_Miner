import datetime
import multiprocessing as mp
import sys
import time
import json
from hashlib import md5
from pathlib import Path as pathlib

from ad_miner.sources.modules import istarmap  # import to apply patch # noqa
import numpy as np
import tqdm
import neo4j  # TO REPLACE BY 'from neo4j import GraphDatabase' after neo4j fix
from urllib.parse import quote


from ad_miner.sources.modules import cache_class, logger, generic_computing
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules.node_neo4j import Node
from ad_miner.sources.modules.path_neo4j import Path
from ad_miner.sources.modules.utils import timer_format, grid_data_stringify
from ad_miner.sources.modules.common_analysis import createGraphPage

MODULES_DIRECTORY = pathlib(__file__).parent

# 🥒 This is a quick import of a fix from @Sopalinge
# 🥒 Following code should be removed when neo4j implements
# 🥒 serialization of neo4j datetime objects
GraphDatabase = neo4j.GraphDatabase


def temporary_fix(cls):
    return (
        cls.__class__,
        (
            cls.year,
            cls.month,
            cls.day,
            cls.hour,
            cls.minute,
            cls.second,
            cls.nanosecond,
            cls.tzinfo,
        ),
    )


neo4j.time.DateTime.__reduce__ = temporary_fix
# End of temporary dirty fix 🥒


def pre_request(arguments):
    driver = GraphDatabase.driver(
        arguments.bolt,
        auth=(arguments.username, arguments.password),
        encrypted=False,
    )
    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                for record in tx.run(
                    "MATCH (a) WHERE a.lastlogon IS NOT NULL return toInteger(a.lastlogon) as last order by last desc LIMIT 1"
                ):
                    date_lastlogon = record.data()

        driver.close()
    except Exception as e:
        logger.print_error("Connection to neo4j database impossible.")
        logger.print_error("The default Bloodhound CE neo4j password is bloodhoundcommunityedition.")
        logger.print_error("The default exegol neo4j database password is exegol4thewin.")
        logger.print_error(e)
        driver.close()
        sys.exit(-1)

    try:
        with driver.session() as session:
            with session.begin_transaction() as tx:
                for record in tx.run(
                    "CALL dbms.components() YIELD versions RETURN versions[0] AS version"
                ):
                    neo4j_version = record.data()

        driver.close()
    except Exception as e:
        logger.print_error("Neo4J could not be found.")
        logger.print_error(e)
        driver.close()
        sys.exit(-1)

    try:
        extract_date = datetime.datetime.fromtimestamp(date_lastlogon["last"]).strftime(
            "%Y%m%d"
        )
    except UnboundLocalError as e:
        logger.print_warning(
            "No LastLogon, the date of the report will be today's date"
        )
        extract_date_timestamp = datetime.date.today()
        extract_date = extract_date_timestamp.strftime("%Y%m%d")

    with driver.session() as session:
        with session.begin_transaction() as tx:
            total_objects = []
            boolean_azure = False
            for record in tx.run(
                "MATCH (x) return labels(x), count(labels(x)) AS number_type"
            ):
                total_objects.append(record.data())

            for record in tx.run("MATCH ()-[r]->() RETURN count(r) AS total_relations"):
                number_relations = record.data()["total_relations"]

            for record in tx.run(
                "MATCH (n) WHERE n.tenantid IS NOT NULL return n LIMIT 1"
            ):
                boolean_azure = bool(record.data()["n"])

    driver.close()

    return neo4j_version, extract_date, total_objects, number_relations, boolean_azure


class Neo4j:
    def __init__(self, arguments, extract_date_int, boolean_azure):
        # remote computers that run requests with their number of core
        if len(arguments.cluster) > 0:
            arguments.nb_chunks = 0
            self.parallelRequest = self.parallelRequestCluster
            self.parallelWriteRequest = self.parallelWriteRequestCluster
            self.writeRequest = self.ClusterWriteRequest

            self.cluster = {}
            list_nodes = arguments.cluster.split(",")
            for node in list_nodes:
                try:
                    ip, port, nCore = node.split(":")
                    self.cluster[ip + ":" + port] = int(nCore)
                    arguments.nb_chunks += 20 * int(nCore)
                except ValueError as e:
                    logger.print_error(
                        "An error occured while parsing the cluster argument. The correct syntax is --cluster ip1:port1:nCores1,ip2:port2:nCores2,etc"
                    )
                    logger.print_error(e)
                    sys.exit(-1)
            if len(self.cluster) == 1:
                # No need to use distributed write requests
                # if there is only one computer
                self.writeRequest = self.simpleRequest
                self.parallelWriteRequest = self.parallelRequestCluster

        else:
            self.parallelRequest = self.parallelRequestLegacy
            self.parallelWriteRequest = self.parallelRequestLegacy
            self.writeRequest = self.simpleRequest

        self.boolean_azure = boolean_azure

        self.extract_date = self.set_extract_date(str(extract_date_int))

        self.gds_cost_type_table = {}

        recursive_level = arguments.level
        self.password_renewal = int(arguments.renewal_password)

        properties = "MemberOf|HasSession|AdminTo|AllExtendedRights|AddMember|ForceChangePassword|GenericAll|GenericWrite|Owns|WriteDacl|WriteOwner|ExecuteDCOM|AllowedToDelegate|ReadLAPSPassword|Contains|GPLink|AddAllowedToAct|AllowedToAct|SQLAdmin|ReadGMSAPassword|HasSIDHistory|CanPSRemote|AddSelf|WriteSPN|AddKeyCredentialLink|SyncLAPSPassword|CanExtractDCSecrets|CanLoadCode|CanLogOnLocallyOnDC|UnconstrainedDelegations|WriteAccountRestrictions|DumpSMSAPassword|Synced|AZRunsAs|SyncedToADUser|SyncedToEntraUser|GoldenCert|WriteGPLink|ADCSESC1|ADCSESC2|ADCSESC3|ADCSESC4|ADCSESC5|ADCSESC6a|ADCSESC6b|ADCSESC7|ADCSESC8|ADCSESC9a|ADCSESC9b|ADCSESC10a|ADCSESC10b|ADCSESC11|ADCSESC12|ADCSESC13|ADCSESC15|DCSync"
        path_to_group_operators_props = properties.replace(
            "|CanExtractDCSecrets|CanLoadCode|CanLogOnLocallyOnDC", ""
        )

        if boolean_azure:
            properties += "|AZAKSContributor|AZAddMembers|AZAddOwner|AZAddSecret|AZAutomationContributor|AZAvereContributor|AZCloudAppAdmin|AZContains|AZContributor|AZExecuteCommand|AZGetCertificates|AZGetKeys|AZGetSecrets|AZGlobalAdmin|AZHasRole|AZKeyVaultContributor|AZLogicAppContributor|AZMGAddMember|AZMGAddOwner|AZMGAddSecret|AZMGAppRoleAssignment_ReadWrite_All|AZMGApplication_ReadWrite_All|AZMGDirectory_ReadWrite_All|AZMGGrantAppRoles|AZMGGrantRole|AZMGGroupMember_ReadWrite_All|AZMGGroup_ReadWrite_All|AZMGRoleManagement_ReadWrite_Directory|AZMGServicePrincipalEndpoint_ReadWrite_All|AZManagedIdentity|AZMemberOf|AZNodeResourceGroup|AZOwner|AZOwns|AZPrivilegedAuthAdmin|AZPrivilegedRoleAdmin|AZResetPassword|AZRunAs|AZScopedTo|AZUserAccessAdministrator|AZVMAdminLogin|AZVMContributor|AZWebsiteContributor"

        if arguments.rdp:
            properties += "|CanRDP"

        self.properties = properties

        inbound_control_edges = "MemberOf|AddSelf|WriteSPN|AddKeyCredentialLink|AddMember|AllExtendedRights|ForceChangePassword|GenericAll|GenericWrite|WriteDacl|WriteOwner|Owns|HasSIDHistory"

        try:
            self.all_requests = json.loads(
                (MODULES_DIRECTORY / "requests.json").read_text(encoding="utf-8")
            )

            del self.all_requests["template"]

            for request_key in self.all_requests.keys():
                # Replace methods with python methods
                self.all_requests[request_key]["output_type"] = {
                    "Graph": Graph,
                    "list": list,
                    "dict": dict,
                }.get(
                    self.all_requests[request_key]["output_type"],
                )
                # Replace variables with their values in requests
                variables_to_replace = {
                    "$extract_date$": int(self.extract_date),
                    "$password_renewal$": int(self.password_renewal),
                    "$properties$": properties,
                    "$path_to_group_operators_props$": path_to_group_operators_props,
                    "$recursive_level$": int(recursive_level),
                    "$inbound_control_edges$": inbound_control_edges,
                }

                fields_to_replace = [
                    "request",
                    "scope_query",
                    "create_gds_graph",
                    "gds_request",
                    "gds_scope_query",
                    "drop_gds_graph",
                ]

                for variable in variables_to_replace.keys():
                    for field in fields_to_replace:
                        if field in self.all_requests[request_key]:

                            self.all_requests[request_key][field] = self.all_requests[
                                request_key
                            ][field].replace(
                                variable, str(variables_to_replace[variable])
                            )

                # Replace postprocessing with python method
                if "postProcessing" in self.all_requests[request_key]:
                    self.all_requests[request_key]["postProcessing"] = {
                        "Neo4j.setDangerousInboundOnGPOs": self.setDangerousInboundOnGPOs,
                        "Neo4j.check_gds_plugin": self.check_gds_plugin,
                        "Neo4j.check_unkown_relations": self.check_unkown_relations,
                        "Neo4j.check_all_domain_objects_exist": self.check_all_domain_objects_exist,
                        "Neo4j.check_relation_type": self.check_relation_type,
                    }.get(self.all_requests[request_key]["postProcessing"])
        except json.JSONDecodeError as error:
            logger.print_error(
                f"Error while parsing neo4j requests from requests.json : \n{error}"
            )
            sys.exit(-1)
        except FileNotFoundError:
            logger.print_error(
                f"Neo4j request file not found : {MODULES_DIRECTORY / 'requests.json'} no such file."
            )
            sys.exit(-1)
        if arguments.gpo_low:
            del self.all_requests["unpriv_users_to_GPO_init"]
            del self.all_requests["unpriv_users_to_GPO_user_enforced"]
            del self.all_requests["unpriv_users_to_GPO_user_not_enforced"]
            del self.all_requests["unpriv_users_to_GPO_computer_enforced"]
            del self.all_requests["unpriv_users_to_GPO_computer_not_enforced"]

        else:  # Deep version of GPO requests
            del self.all_requests["unpriv_users_to_GPO"]
        try:
            self.edges_rating = json.loads(
                (MODULES_DIRECTORY / "exploitability_ratings.json").read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as error:
            logger.print_error(
                f"Error while parsing exploitability ratings from exploitability_ratings.json : \n{error}"
            )
            sys.exit(-1)
        except FileNotFoundError:
            logger.print_error(
                f"Exploitability ratings file not found : {MODULES_DIRECTORY / 'exploitability_ratings.json'} no such file."
            )
            sys.exit(-1)

        try:
            # Setup driver
            self.driver = GraphDatabase.driver(
                arguments.bolt,
                auth=(arguments.username, arguments.password),
                encrypted=False,
            )

            self.arguments = arguments
            self.cache_enabled = arguments.cache
            self.cache = cache_class.Cache(arguments)

        except Exception as e:
            logger.print_error("Connection to neo4j database impossible.")
            logger.print_error(e)
            sys.exit(-1)

    def close(self):
        self.driver.close()

    @staticmethod
    def executeParallelRequest(
        value, identifier, query, arguments, output_type, server, gds_cost_type_table
    ):
        """This function is used in multiprocessing pools
        to execute multiple query parts in parallel"""
        q = query.replace("PARAM1", str(value)).replace("PARAM2", str(identifier))
        result = []
        bolt = server if server.startswith("bolt://") else "bolt://" + server
        driver = GraphDatabase.driver(
            bolt,
            auth=(arguments.username, arguments.password),
            encrypted=False,
        )
        with driver.session() as session:
            with session.begin_transaction() as tx:
                if output_type is Graph:
                    for record in tx.run(q):
                        result.append(record["p"])
                        # Quick way to handle multiple records
                        # (e.g., RETURN p, p2)
                        if "p2" in record:
                            result.append(record["p2"])
                    try:
                        result = Neo4j.computePathObject(result, gds_cost_type_table)
                    except Exception as e:
                        logger.print_error(
                            "An error while computing path object of this query:\n" + q
                        )
                        logger.print_error(e)

                else:
                    result = tx.run(q)
                    if output_type is list:
                        result = result.values()
                    else:  # then it should be dict ?
                        result = result.data()

        return result

    @staticmethod
    def process_request(self, request_key):
        if self.cache_enabled:  # If cache enable, try to retrieve from cache
            result = self.cache.retrieveCacheEntry(request_key)
            if result is None:
                result = []
            if result is not False:  # Sometimes result = []
                logger.print_debug(
                    "From cache : %s - %d objects"
                    % (self.all_requests[request_key]["name"], len(result))
                )
                self.all_requests[request_key]["result"] = result
                if "postProcessing" in self.all_requests[request_key]:
                    self.all_requests[request_key]["postProcessing"](self, result)
                return result

        request = self.all_requests[request_key]
        logger.print_debug("Requesting : %s" % request["name"])
        start = time.time()
        result = []

        # Create neo4j GDS graph if plugin installed and request adapted
        # Also replace the classic request and scope query with the GDS ones
        if "is_a_gds_request" in request and self.gds:
            q = request["create_gds_graph"]
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    tx.run(q)

            request["request"] = request["gds_request"]

            if "gds_scope_query" in request:
                request["scope_query"] = request["gds_scope_query"]
            elif "scope_query" in request:
                del request["scope_query"]

        if "scope_query" in request:
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    scopeQuery = request["scope_query"]
                    if tx.run(scopeQuery).value() != []:
                        scopeSize = tx.run(scopeQuery).value()[0]
                    else:
                        scopeSize = 0

            part_number = int(self.arguments.nb_chunks)
            part_number = min(scopeSize, part_number)

            print(f"scope size : {str(scopeSize)} | nb chunks : {part_number}")
            items = []
            space = np.linspace(0, scopeSize, part_number + 1, dtype=int)
            output_type = self.all_requests[request_key]["output_type"]

            # Divide the request with SKIP & LIMIT
            for i in range(len(space) - 1):
                items.append(
                    [
                        space[i],
                        space[i + 1] - space[i],
                        request["request"],
                        self.arguments,
                        output_type,
                        self.gds_cost_type_table,
                    ]
                )

            if "is_a_write_request" in request:
                result = self.parallelWriteRequest(self, items)
            else:
                result = self.parallelRequest(self, items)

        elif "is_a_write_request" in request:  # Not parallelized write request
            result = self.writeRequest(self, request_key)
        else:  # Simple not parallelized read request
            result = self.simpleRequest(self, request_key)

        if result is None:
            result = []

        if (
            "is_a_gds_request" in request
            and self.gds
            and "reverse_path" in request
            and request["reverse_path"]
        ):
            for path in result:
                path.reverse()

        if "postProcessing" in request:
            request["postProcessing"](self, result)

        # If GDS installed and request adapted, dropping previously created graph
        if "is_a_gds_request" in request and self.gds:
            q = request["drop_gds_graph"]
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    tx.run(q)

        self.cache.createCacheEntry(request_key, result)
        logger.print_warning(
            timer_format(time.time() - start) + " - %d objects" % len(result)
        )
        request["result"] = result
        return result

    @staticmethod
    def simpleRequest(self, request_key):
        request = self.all_requests[request_key]
        output_type = request["output_type"]
        result = []
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                if output_type is Graph:
                    for record in tx.run(request["request"]):
                        result.append(record["p"])
                        # Quick way to handle multiple records
                        # (e.g., RETURN p, p2)
                        if "p2" in record:
                            result.append(record["p2"])
                    result = self.computePathObject(result, self.gds_cost_type_table)
                else:
                    result = tx.run(request["request"])
                    if output_type is list:
                        result = result.values()
                    else:
                        result = result.data()
        return result

    @staticmethod
    def ClusterWriteRequest(self, request_key):
        """This function ensure that simple write
        queries are executed to all nodes of a cluster"""
        starting_time = time.time()
        cluster_state = {server: False for server in self.cluster.keys()}
        query = self.all_requests[request_key]["request"]
        items = [  # Create all requests to do
            (
                -1,
                -1,
                query,
                self.arguments,
                self.all_requests[request_key]["output_type"],
                server,
                self.gds_cost_type_table,
            )
            for server in self.cluster.keys()
        ]

        with mp.Pool(len(self.cluster)) as pool:
            result = []
            tasks = {}
            for item in items:
                tasks[item[5]] = pool.apply_async(self.executeParallelRequest, item)
            while not all(task.ready() for task in tasks.values()):
                time.sleep(0.01)
                for server in tasks.keys():
                    if tasks[server].ready() and not cluster_state[server]:
                        cluster_state[server] = True
                        logger.print_success(
                            "Write query executed by "
                            + server
                            + " in "
                            + str(round(time.time() - starting_time, 2))
                            + "s."
                        )
            temp_results = [task.get() for task in tasks.values()]
            result = temp_results[0]
            # Same request executed on every node, we only need the result once
        return result

    @staticmethod
    def parallelRequestCluster(self, items):
        """parallelRequestCluster is able to distribute parts of a
        complex request to multiple computers"""
        if len(items) == 0:
            return []
        output_type = items[0][4]
        # Total CPU units of all node of the cluster
        max_parallel_requests = sum(self.cluster.values())

        result = []
        requestList = items.copy()

        pbar = tqdm.tqdm(total=len(requestList), desc="Cluster participation:\n")

        temp_results = []

        def process_completed_task(
            number_of_retrieved_objects, task, active_jobs, jobs_done, pbar
        ):
            temporary_result = task.get()
            # Update displayed number of retrieved objects
            if output_type == list:
                if len(temporary_result) > 0:
                    for sublist in temporary_result:
                        number_of_retrieved_objects += len(sublist)
            elif output_type == dict or output_type == Graph:
                number_of_retrieved_objects += len(temporary_result)

            temporary_result = None

            active_jobs[server].remove(task)
            jobs_done[server] += 1
            total_jobs_done = sum(jobs_done.values())
            cluster_participation = ""
            for server_running in jobs_done:
                server_name = server_running.split(":")[0]
                cluster_participation += (
                    server_name
                    + ": "
                    + str(
                        int(
                            round(
                                100 * jobs_done[server_running] / total_jobs_done,
                                0,
                            )
                        )
                    )
                    + "% "
                )
            pbar.set_description(
                cluster_participation
                + "| "
                + str(number_of_retrieved_objects)
                + " objects"
            )
            pbar.refresh()
            pbar.update(1)
            return number_of_retrieved_objects

        with mp.Pool(processes=max_parallel_requests) as pool:
            # Dict that keep track of which server is executing which requests
            active_jobs = dict((server, []) for server in self.cluster)

            # Dict that keep track of how many queries each server did
            jobs_done = dict((server, 0) for server in self.cluster)

            # Counter to keep track of how many objects have been retrieved
            number_of_retrieved_objects = 0

            while len(requestList) > 0:
                time.sleep(0.01)

                for server, max_jobs in self.cluster.items():
                    if len(requestList) == 0:
                        break
                    for task in active_jobs[server]:
                        if task.ready():
                            number_of_retrieved_objects = process_completed_task(
                                number_of_retrieved_objects,
                                task,
                                active_jobs,
                                jobs_done,
                                pbar,
                            )

                    if len(active_jobs[server]) < max_jobs:
                        item = requestList.pop()
                        (
                            value,
                            identifier,
                            query,
                            arguments,
                            output_type,
                            self.gds_cost_type_table,
                        ) = item

                        task = pool.apply_async(
                            self.executeParallelRequest,
                            (
                                value,
                                identifier,
                                query,
                                arguments,
                                output_type,
                                server,
                                self.gds_cost_type_table,
                            ),
                        )
                        temp_results.append(task)
                        active_jobs[server].append(task)

            # Waiting for every task to finish
            # Not in the main loop for better efficiency

            while not all(len(tasks) == 0 for tasks in active_jobs.values()):
                time.sleep(0.01)
                for server, max_jobs in self.cluster.items():
                    for task in active_jobs[server]:
                        if task.ready():
                            number_of_retrieved_objects = process_completed_task(
                                number_of_retrieved_objects,
                                task,
                                active_jobs,
                                jobs_done,
                                pbar,
                            )
            for r in temp_results:
                result += r.get()
        pbar.close()
        return result

    @staticmethod
    def parallelRequestLegacy(self, items):
        """parallelRequestLegacy is the default way of slicing requests
        in smaller requests to parallelize it"""
        items = [  # Add bolt to items
            (
                value,
                identifier,
                query,
                arguments,
                output_type,
                self.arguments.bolt,
                gds_cost_type_table,
            )
            for value, identifier, query, arguments, output_type, gds_cost_type_table in items
        ]

        with mp.Pool(mp.cpu_count()) as pool:
            result = []
            for _ in tqdm.tqdm(
                pool.istarmap(self.executeParallelRequest, items),
                total=len(items),
            ):
                result += _
        return result

    @staticmethod
    def setDangerousInboundOnGPOs(self, data):
        print("Entering Post processing")
        ids = []
        for d in data:
            ids.append(d.nodes[-1].id)
        q = "MATCH (g) WHERE ID(g) in " + str(ids) + " SET g.dangerous_inbound=TRUE"
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                tx.run(q)

    @staticmethod
    def set_extract_date(date):
        year = int(date[0:4])
        month = int(date[4:6])
        day = int(date[6:8])
        date_time = datetime.datetime(year, month, day)
        return time.mktime(date_time.timetuple())

    @staticmethod
    def requestNamesAndHash(server, username, password):
        """requestNamesAndHash returns the md5 hash of the
        concatenation of all nodes names and is used by verify_integrity()"""
        q = "MATCH (a) RETURN ID(a),a.name"
        bolt = "bolt://" + server

        driver = GraphDatabase.driver(
            bolt,
            auth=(username, password),
            encrypted=False,
        )

        names = ""

        with driver.session() as session:
            with session.begin_transaction() as tx:
                for record in tx.run(q):
                    names += str(record["a.name"])

        driver.close()
        hash = md5(names.encode(), usedforsecurity=False).hexdigest()
        logger.print_debug("Hash for " + server + " is " + hash)
        return hash

    @staticmethod
    def verify_integrity(self):
        """
        Hash the names of all nodes to avoid obvious errors
        (like trying to use two completely different neo4j databases)
        """
        if len(self.cluster) == 1:
            return
        startig_time = time.time()
        logger.print_debug("Starting integrity check")
        hashes = []
        temp_results = []
        username = self.arguments.username
        password = self.arguments.password

        with mp.Pool(processes=self.arguments.nb_cores) as pool:
            for server in self.cluster.keys():
                task = pool.apply_async(
                    Neo4j.requestNamesAndHash,
                    (
                        server,
                        username,
                        password,
                    ),
                )
                temp_results.append(task)

            for task in temp_results:
                try:
                    hashes.append(task.get())
                except Exception as e:
                    errorMessage = "Connection to neo4j database refused."
                    logger.print_error(errorMessage)
                    logger.print_error(e)
                    sys.exit(-1)

        if all(hash == hashes[0] for hash in hashes):
            logger.print_success("All databases seems to be the same.")
        else:
            logger.print_error("Be careful, the database on the nodes seems different.")

        stopping_time = time.time()

        logger.print_warning(
            "Integrity check took " + str(round(stopping_time - startig_time, 2)) + "s"
        )

    @staticmethod
    def parallelWriteRequestCluster(self, items):
        """parallelWriteRequestCluster ensures that a parallelised write
        request is done to each neo4j database"""
        starting_time = time.time()
        result = []
        if len(items) == 0:
            return result

        output_type = items[0][4]

        small_requests_to_do = {
            server: [
                (value, identifier, query, arguments, output_type, server)
                for value, identifier, query, arguments, output_type in items
            ]
            for server in self.cluster.keys()
        }
        cluster_state = {server: False for server in self.cluster.keys()}

        pbar = tqdm.tqdm(
            total=sum(len(lst) for lst in small_requests_to_do.values()),
            desc="Executing write query to all cluster nodes",
        )

        # Total CPU units of all node of the cluster
        max_parallel_requests = sum(self.cluster.values())

        temp_results = []

        with mp.Pool(processes=max_parallel_requests) as pool:
            # Dict that keep track of which server is executing which requests
            active_jobs = dict((server, []) for server in self.cluster)

            while sum(len(lst) for lst in small_requests_to_do.values()) > 0:
                time.sleep(0.01)

                for server, max_jobs in self.cluster.items():
                    if sum(len(lst) for lst in small_requests_to_do.values()) == 0:
                        break
                    for task in active_jobs[server]:
                        if task.ready():
                            active_jobs[server].remove(task)
                            pbar.update(1)
                    if (
                        len(small_requests_to_do[server]) == 0
                        and len(active_jobs[server]) == 0
                        and not cluster_state[server]
                    ):
                        cluster_state[server] = True
                        logger.print_success(
                            "Write request executed by "
                            + server
                            + " in "
                            + str(round(time.time() - starting_time, 2))
                            + "s."
                        )
                    if (
                        len(active_jobs[server]) < max_jobs
                        and len(small_requests_to_do[server]) > 0
                    ):
                        item = small_requests_to_do[server].pop()
                        (
                            value,
                            identifier,
                            query,
                            arguments,
                            output_type,
                            server,
                        ) = item

                        task = pool.apply_async(
                            self.executeParallelRequest,
                            (
                                value,
                                identifier,
                                query,
                                arguments,
                                output_type,
                                server,
                                self.gds_cost_type_table,
                            ),
                        )
                        if server == next(iter(self.cluster)):
                            temp_results.append(task)
                        active_jobs[server].append(task)

            # Waiting for every task to finish
            # Not in the main loop for better efficiency

            while not all(len(tasks) == 0 for tasks in active_jobs.values()):
                time.sleep(0.01)
                for server, max_jobs in self.cluster.items():
                    for task in active_jobs[server]:
                        if task.ready():
                            active_jobs[server].remove(task)
                            pbar.update(1)
                    if (
                        len(small_requests_to_do[server]) == 0
                        and len(active_jobs[server]) == 0
                        and not cluster_state[server]
                    ):
                        cluster_state[server] = True
                        logger.print_success(
                            "Write request executed to "
                            + server
                            + " in "
                            + str(round(time.time() - starting_time, 2))
                            + "s."
                        )
            for r in temp_results:
                result += r.get()
        pbar.close()
        return result

    @classmethod
    def computePathObject(self, Paths, gds_cost_type_table):
        """computePathObject allows object to be serialized and should
        be used when output_type == Graph"""
        final_paths = []
        for path in Paths:
            if path is not None:
                nodes = []
                for relation in path.relationships:
                    rtype = relation.type
                    if "PATH_" in rtype:
                        gds_identifier = round(float(relation.get("cost")), 3)
                        gds_identifier = round(1000 * (gds_identifier % 1))

                        rtype = gds_cost_type_table[gds_identifier]

                    for node in relation.nodes:
                        label = [i for i in node.labels if "Base" not in i][
                            0
                        ]  # e.g. : {"User","Base"} -> "User" or {"User","AZBase"} -> "User"
                        nodes.append(
                            Node(
                                node.id,
                                label,
                                node["name"],
                                node["domain"],
                                node["tenantid"],
                                rtype,
                            )
                        )
                        break

                nodes.append(
                    Node(
                        path.end_node.id,
                        [i for i in path.end_node.labels if "Base" not in i][0],
                        path.end_node["name"],
                        path.end_node["domain"],
                        path.end_node["tenantid"],
                        "",
                    )
                )

                final_paths.append(Path(nodes))

        return final_paths

    @staticmethod
    def check_gds_plugin(self, result):
        """Verify if graph data science plugin installed
        on the neo4j database. Set a flag accordingly."""
        self.gds = result[0]["gds_installed"]
        assert type(self.gds) is bool
        if self.gds:
            logger.print_success("GDS plugin installed.")
            logger.print_success("Using exploitability for paths computation.")

            # If GDS is installed, drop all existing graphs to avoid conflicts
            q = "CALL gds.graph.list() YIELD graphName RETURN graphName"
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    result = tx.run(q).values()
                existing_graphs = [el[0] for el in result]
                for g in existing_graphs:
                    logger.print_debug("Deleting " + g + "graph to prevent conflicts")
                    q = "CALL gds.graph.drop('" + g + "') YIELD graphName;"
                    with session.begin_transaction() as tx:
                        tx.run(q)

        else:
            logger.print_magenta("GDS plugin not installed.")
            logger.print_magenta("Not using exploitability for paths computation.")

    @staticmethod
    def check_unkown_relations(self, result):
        if self.gds:
            logger.print_warning("Setting exploitability ratings to edges.")
            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    for r in self.edges_rating.keys():
                        cost = self.edges_rating[r]
                        q = "MATCH ()-[r:"
                        q += str(r)
                        q += "]->() SET r.cost="
                        q += str(cost)

                        tx.run(q)

            relation_list = [r[0] for r in result]

            with self.driver.session() as session:
                with session.begin_transaction() as tx:
                    for i in range(len(relation_list)):
                        r = relation_list[i]
                        if r not in self.edges_rating.keys():
                            logger.print_warning(
                                r
                                + " relation type is unknown and will use default exploitability rating."
                            )
                        q = "MATCH ()-[r:"
                        q += str(r)
                        q += "]->() SET r.cost=r.cost + "
                        q += str(round(i / 1000, 3))
                        tx.run(q)
                        self.gds_cost_type_table[i] = r

    def compute_common_cache(self, requests_results):
        """
        This function aims to pre compute data that will be reused often in controls.
        It adds it to the requests_results dictionnary
        It is mainly populated with legacy code from domains.py, computers.py, etc
        """
        computers_with_last_connection_date = requests_results[
            "computers_not_connected_since"
        ]
        groups = requests_results["nb_groups"]
        computers_nb_domain_controllers = requests_results["nb_domain_controllers"]
        users_dormant_accounts = requests_results["dormant_accounts"]
        users_nb_domain_admins = requests_results["nb_domain_admins"]

        computers_not_connected_since_60 = list(
            filter(
                lambda computer: int(computer["days"]) > 60,
                computers_with_last_connection_date,
            )
        )
        users_not_connected_for_3_months = (
            [user["name"] for user in users_dormant_accounts if user["days"] > 90]
            if users_dormant_accounts is not None
            else None
        )

        dico_ghost_computer = {}
        if computers_not_connected_since_60 != []:
            for dico in computers_not_connected_since_60:
                dico_ghost_computer[dico["name"]] = True

        requests_results["dico_ghost_computer"] = dico_ghost_computer

        dico_ghost_user = {}
        if users_not_connected_for_3_months != None:
            for username in users_not_connected_for_3_months:
                dico_ghost_user[username] = True

        requests_results["dico_ghost_user"] = dico_ghost_user

        dico_dc_computer = {}
        if computers_nb_domain_controllers != None:
            for dico in computers_nb_domain_controllers:
                dico_dc_computer[dico["name"]] = True
        requests_results["dico_dc_computer"] = dico_dc_computer

        dico_da_group = {}
        if groups != None:
            for dico in groups:
                if dico.get("da"):
                    dico_da_group[dico["name"]] = True
        requests_results["dico_da_group"] = dico_da_group

        dico_user_da = {}
        if users_nb_domain_admins != []:
            for dico in users_nb_domain_admins:
                dico_user_da[dico["name"]] = True
        requests_results["dico_user_da"] = dico_user_da

        admin_list = []
        for admin in users_nb_domain_admins:
            admin_list.append(admin["name"])
        requests_results["admin_list"] = admin_list

        objects_to_domain_admin = requests_results["objects_to_domain_admin"]
        users_to_domain_admin = {}
        groups_to_domain_admin = {}
        computers_to_domain_admin = {}
        ou_to_domain_admin = {}
        gpo_to_domain_admin = {}
        domains_to_domain_admin = {}

        domains = requests_results["domains"]
        for domain in domains:

            computers_to_domain_admin[domain[0]] = []
            users_to_domain_admin[domain[0]] = []
            groups_to_domain_admin[domain[0]] = []
            ou_to_domain_admin[domain[0]] = []
            gpo_to_domain_admin[domain[0]] = []

        logger.print_debug("Split objects into types...")
        for path in objects_to_domain_admin:
            if "User" in path.nodes[0].labels:
                users_to_domain_admin[path.nodes[-1].domain].append(path)
            elif "Computer" in path.nodes[0].labels:
                computers_to_domain_admin[path.nodes[-1].domain].append(path)
            elif "Group" in path.nodes[0].labels:
                groups_to_domain_admin[path.nodes[-1].domain].append(path)
            elif "OU" in path.nodes[0].labels:
                ou_to_domain_admin[path.nodes[-1].domain].append(path)
            elif "GPO" in path.nodes[0].labels:
                gpo_to_domain_admin[path.nodes[-1].domain].append(path)
            elif "Domain" in path.nodes[0].labels:
                domains_to_domain_admin.append(path)
        logger.print_debug("[Done]")

        requests_results["users_to_domain_admin"] = users_to_domain_admin
        requests_results["groups_to_domain_admin"] = groups_to_domain_admin
        requests_results["computers_to_domain_admin"] = computers_to_domain_admin
        requests_results["ou_to_domain_admin"] = ou_to_domain_admin
        requests_results["gpo_to_domain_admin"] = gpo_to_domain_admin
        requests_results["domains_to_domain_admin"] = domains_to_domain_admin

        logger.print_debug("Split paths to DA...")

        dico_users_to_da = {}
        dico_groups_to_da = {}
        dico_computers_to_da = {}
        dico_ou_to_da = {}
        dico_gpo_to_da = {}

        for path in objects_to_domain_admin:

            if "User" in path.nodes[0].labels:
                if path.nodes[0].name not in dico_users_to_da:
                    dico_users_to_da[path.nodes[0].name] = []
                dico_users_to_da[path.nodes[0].name].append(path)

            elif "Computer" in path.nodes[0].labels:
                if path.nodes[0].name not in dico_computers_to_da:
                    dico_computers_to_da[path.nodes[0].name] = []
                dico_computers_to_da[path.nodes[0].name].append(path)

            elif "Group" in path.nodes[0].labels:
                if path.nodes[0].name not in dico_groups_to_da:
                    dico_groups_to_da[path.nodes[0].name] = []
                dico_groups_to_da[path.nodes[0].name].append(path)

            elif "OU" in path.nodes[0].labels:
                if path.nodes[0].name not in dico_ou_to_da:
                    dico_ou_to_da[path.nodes[0].name] = []
                dico_ou_to_da[path.nodes[0].name].append(path)

            elif "GPO" in path.nodes[0].labels:
                if path.nodes[0].name not in dico_gpo_to_da:
                    dico_gpo_to_da[path.nodes[0].name] = []
                dico_gpo_to_da[path.nodes[0].name].append(path)

        requests_results["dico_users_to_da"] = dico_users_to_da
        requests_results["dico_computers_to_da"] = dico_computers_to_da
        requests_results["dico_groups_to_da"] = dico_groups_to_da
        requests_results["dico_ou_to_da"] = dico_ou_to_da
        requests_results["dico_gpo_to_da"] = dico_gpo_to_da

        logger.print_debug("[Done]")

        try:
            if not requests_results["users_admin_on_servers_1"]:
                requests_results["users_admin_on_servers_1"] = []
            if not requests_results["users_admin_on_servers_2"]:
                requests_results["users_admin_on_servers_2"] = []

            users_admin_on_servers_all_data = (
                requests_results["users_admin_on_servers_1"]
                + requests_results["users_admin_on_servers_2"]
            )
            users_admin_on_servers_all_data = [
                dict(t) for t in {tuple(d.items()) for d in users_admin_on_servers_all_data}
            ]
            users_admin_on_servers = generic_computing.getCountValueFromKey(
                users_admin_on_servers_all_data, "computer"
            )
            users_admin_on_servers_list = generic_computing.getListAdminTo(
                users_admin_on_servers_all_data,
                "computer",
                "user",
            )

            if users_admin_on_servers is not None and users_admin_on_servers != {}:
                servers_with_most_paths = users_admin_on_servers[
                    list(users_admin_on_servers.keys())[0]
                ]
            else:
                servers_with_most_paths = []

            requests_results["users_admin_on_servers_list"] = users_admin_on_servers_list
            requests_results["servers_with_most_paths"] = servers_with_most_paths
            requests_results["users_admin_on_servers"] = users_admin_on_servers
            requests_results["users_admin_on_servers_all_data"] = (
                users_admin_on_servers_all_data
            )
        except KeyError as ke:
            print(f"KeyError: {ke}")

        # Dico for ACL anomaly and futur other controls to retrieve paths to DA on computer ID
        dico_paths_computers_to_DA = {}
        for domain in computers_to_domain_admin:
            for path in computers_to_domain_admin[domain]:
                if path.nodes[0].name not in dico_paths_computers_to_DA:
                    dico_paths_computers_to_DA[path.nodes[0].name] = []
                dico_paths_computers_to_DA[path.nodes[0].name].append(path)
        requests_results["dico_paths_computers_to_DA"] = dico_paths_computers_to_DA

        users_admin_on_computers = requests_results["users_admin_on_computers"]
        dico_is_user_admin_on_computer = {}
        for d in users_admin_on_computers:
            dico_is_user_admin_on_computer[d["user"]] = True
        requests_results["dico_is_user_admin_on_computer"] = (
            dico_is_user_admin_on_computer
        )

        # Dico for kerberoastable users to add them to graphs
        dico_is_kerberoastable = {}
        for d in requests_results["nb_kerberoastable_accounts"]:
            dico_is_kerberoastable[d["name"]] = True

        requests_results["dico_is_kerberoastable"] = dico_is_kerberoastable

        list_computers_admin_computers = requests_results[
            "computers_admin_on_computers"
        ]
        computers_admin_to_count = generic_computing.getCountValueFromKey(
            list_computers_admin_computers, "source_computer"
        )
        requests_results["computers_admin_to_count"] = computers_admin_to_count

    @staticmethod
    def check_all_domain_objects_exist(self, result):
        objects_with_unexisting_domains = result[0][0]

        if objects_with_unexisting_domains > 0:
            error_message = f"Warning: {objects_with_unexisting_domains} objects have a domain attribute that does not correspond to any domain object.\n"
            error_message += "This is often due to using the Bloodhound Community Edition ingestor while data has been collected with the old Sharphound collector.\n"
            error_message += "The database lacks some paths due to these unexisting domain objects and AD Miner will probably crash.\n\n"
            error_message += "The AD Miner team advise to use these combinations :\n\n"
            error_message += "Sharphound v1 -> Old Bloodhound Client (https://github.com/BloodHoundAD/BloodHound)\n"
            error_message += "Sharphound v2 -> Bloodhound Community Edition (https://github.com/SpecterOps/BloodHound)"

            logger.print_error(error_message)

    @staticmethod
    def check_relation_type(self, result):
        """Compares $properties$ and relations existing in the database."""
        properties_relation_list = self.properties.split("|")
        # TODO remove relations that we don't want to see in the warning here.

        database_relation_list = [d["relationType"] for d in result]

        unusable_properties = [
            "DCFor",
            "Enroll",
            "ManageCA",
            "ManageCertificates",
            "RootCAFor",
            "TrustedBy",
            "GetChanges",
            "GetChangesInFilteredSet",
            "GetChangesAll",
            "NTAuthStoreFor",
            "IssuedSignedBy",
            "TrustedForNTAuth",
            "EnterpriseCAFor",
            "PublishedTo",
            "HostsCAService",
            "RemoteInteractiveLogonPrivilege",
            "EnrollOnBehalfOf",
            "ManageCA",
        ]

        if not self.arguments.rdp:
            unusable_properties.append("CanRDP")

        # Remove properties that we don't wan't to use
        for property in unusable_properties:
            if property in database_relation_list:
                database_relation_list.remove(property)

        unused_relations = ""
        for relation in database_relation_list:
            if relation not in properties_relation_list:
                unused_relations += relation + ", "

        unused_relations = unused_relations[:-2]

        if len(unused_relations) > 0:
            logger.print_error(
                "The following relations are not used (yet) for general AD Miner path finding:"
            )
            logger.print_error(unused_relations)
