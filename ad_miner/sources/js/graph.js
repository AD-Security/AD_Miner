// This object is used by vis.js to retrieve node icon
var icon_group_options = {};

var existing_attribute_strings = []

for (var i = 0; i < window.data_nodes.length; i++) {

  // Creates a string to describe each nodes and its attribute
  // to create the object that will contain each icon for vis.js
  var node_attribute_string = "";

  node_attribute_string = node_attribute_string.concat(window.data_nodes[i].instance);

  node_attribute_string = node_attribute_string.concat('_');
  node_attribute_string = node_attribute_string.concat(window.data_nodes[i].position);

  window.data_nodes[i].attributes.sort();
  for (var j = 0; j < window.data_nodes[i].attributes.length; j++) {
    node_attribute_string = node_attribute_string.concat('_');
    node_attribute_string = node_attribute_string.concat(window.data_nodes[i].attributes[j]);
  }

  window.data_nodes[i].group = node_attribute_string;

  if (!existing_attribute_strings.includes(node_attribute_string)) {
    existing_attribute_strings.push(node_attribute_string);
  }
}

for (var i = 0; i < existing_attribute_strings.length; i++) {
  icon_group_options[existing_attribute_strings[i]] = {
    image: get_image(existing_attribute_strings[i]),
    shadow: { enabled: true }
  }
}

//hierarchical_options
var options = {
  layout: {
    // hierarchical: {
    //     direction: "LR",
    //     //sortMethod: "directed",
    //     nodeSpacing: 200,
    // },
  },

  physics: {
    enabled: false,
  },

  interaction: { dragNodes: true },

  nodes: {
    size: 25,
    shape: 'image',
  },
  edges: {
    smooth: {
      type: 'cubicBezier',
      roundness: 0.4,
    },
    color: 'rgba(119, 119, 119, 1)',
    arrows: 'to',
    length: 250,
  },
  groups: icon_group_options,
};

window.highlightActive = false;

// In the copy variables, we store the data of the full graph
// while the other variables (allNodes, allEdges) will only store the data of the current view.

dico_edges_children = {};
dico_edges_children_inverted = {};

for (var i = 0; i < data_edges.length; i++) {
  if (dico_edges_children[data_edges[i].from] === undefined) {
    dico_edges_children[data_edges[i].from] = [data_edges[i].to];
  } else {
    dico_edges_children[data_edges[i].from].push(data_edges[i].to);
  }

  if (dico_edges_children_inverted[data_edges[i].to] === undefined) {
    dico_edges_children_inverted[data_edges[i].to] = [data_edges[i].from];
  } else {
    dico_edges_children_inverted[data_edges[i].to].push(data_edges[i].from);
  }
}

var dico_nodes = {};
for (var i = 0; i < data_nodes.length; i++) {
  dico_nodes[data_nodes[i].id] = data_nodes[i];
}

var url = new URL(window.location.href);
var node_parameter = url.searchParams.get('node');
if (node_parameter != null) {
  array_data = display_only_path_from_node(parseInt(node_parameter));
  data_nodes = array_data[0];
  data_edges = array_data[1];
  change_dropdown_endnodes(data_nodes);
  selection_end_node(data_nodes);
}
else {
  change_dropdown_endnodes(data_nodes);
}

initNetwork(data_nodes, data_edges);
network.fit();

displayHideText(document.getElementById('switchHideText'));

// Return the ID of edges that link two nodes from different domains
function getChangeOfDomain(nodesList, edgesList) {
  var taggedEdgesKeys = [];
  for (const [key, value] of Object.entries(edgesList)) {
    var start_node_domain = nodesList[value['from']]['domain'];
    var end_node_domain = nodesList[value['to']]['domain'];
    if (start_node_domain !== end_node_domain) {
      taggedEdgesKeys.push(key);
    }
  }
  return taggedEdgesKeys;
}

// Color edges that link two nodes from different domains
function colorTaggedEdges(taggedEdgesKeys) {
  for (const edgeKey of taggedEdgesKeys) {
    edges.update({id: edgeKey, color: {color: 'rgba(102, 0, 204, 1)'}, dashes: true, width: 3});
  }
}

// Initializes and starts the network
function initNetwork(n, e) {
  nodesdeepcopy = new vis.DataSet(n);
  edgesdeepcopy = new vis.DataSet(e);
  allNodescopy = nodesdeepcopy.get({ returnType: 'Object' });
  // allEdgescopy = edgesdeepcopy.get({returnType:"Object"});
  allClusters = {};
  // Cluster nodes with more than 3 lone direct children (and cluster only these children)
  markClustersPartial(3);
  // Cluster all nodes with more than 100 direct children (and cluster all children recursively)
  markClusters(100);

  // Cluster nodes that are OUs and that have more than 3 direct children that are ending nodes
  markClustersForward(3);
  var subnetTuple = getSubnet();
  var subnodes = subnetTuple[0];
  var subedges = subnetTuple[1];
  // Uncomment next 2 lines to disable clustering
  // const nodes = new vis.DataSet(data_nodes);
  // const edges = new vis.DataSet(data_edges);

  // Comment next 2 lines to disable clustering
  nodes = new vis.DataSet(Object.values(subnodes));
  edges = new vis.DataSet(Object.values(subedges));

  var nodesView = new vis.DataView(nodes);
  var edgesView = new vis.DataView(edges);

  startNetwork({ nodes: nodesView, edges: edgesView }, options);
}

// Create network, set the allNodes and allEdges variables
function startNetwork(data, opts) {
  const container = document.getElementById('mynetwork');

  // assigning undeclared variables makes them global :))
  network = new vis.Network(container, data, opts);
  allNodes = nodes.get({ returnType: 'Object' });
  tmp_allEdges = edges.get({ returnType: 'Object' });

  allEdges = manageMultipleEdges(tmp_allEdges);

  taggedEdges = getChangeOfDomain(allNodes, allEdges);
  colorTaggedEdges(taggedEdges);

  bindRightClick(); // attach context menu to new network object

  // if (!network.layoutEngine.options.hierarchical.enabled) { // Deactivate for hierarchical
  //   changeNodeSize(60,110);
  // }

  // For loading bar
  // var startTime = Date.now();
  // document.getElementById('nbNodes').innerText = Object.keys(allNodes).length;
  // document.getElementById('nbEdges').innerText = Object.keys(allEdges).length;

  network.on('click', neighbourhoodHighlight);
  network.on('click', hideSearchResults);
  //bindEvents(); // attach context menu to new network object

  // let array_position = percentage_path_passing_through_nodes();

  nodes_positioning();
}

function updateGraph(nodeId) {
  subnetTuple = getSubnet();
  subnodes = subnetTuple[0];
  subedges = subnetTuple[1];

  // Uncomment next 2 lines to disable clustering
  // const nodes = new vis.DataSet(data_nodes);
  // const edges = new vis.DataSet(data_edges);

  // Comment next 2 lines to disable clustering
  nodes = new vis.DataSet(Object.values(subnodes));
  edges = new vis.DataSet(Object.values(subedges));

  nodesView = new vis.DataView(nodes);
  edgesView = new vis.DataView(edges);

  const x_anchor = allNodes[nodeId].x;
  const y_anchor = allNodes[nodeId].y;

  const x_view = network.getViewPosition().x;
  const y_view = network.getViewPosition().y;

  const scale = network.getScale();

  startNetwork({ nodes: nodesView, edges: edgesView }, options);

  const x = allNodes[nodeId].x;
  const y = allNodes[nodeId].y;

  var moveToOptions = {
    position: {
      x: x_view + (x - x_anchor),
      y: y_view + (y - y_anchor),
    }, // position to animate to
    scale: scale, // scale to animate to
  };
  network.moveTo(moveToOptions);
}
// data_nodes and data_edges are defined when the html report is generated.
// the two variables are written to the file by the graph_class.py file.

function manageMultipleEdges(edges) {
  // split edges in case of multiple of them going from the same origin node to the same destination node
  if (Object.entries(edges).length > 1000) {
    return edges
  }
  to_smooth = [];
  // Find "sibling" edges
  for (var [key, value] of Object.entries(edges)) {
    sibling_edges = [[key, 1]];
    for (var [key2, value2] of Object.entries(edges)) {
      if ((value["to"] == value2["to"] && value["from"] == value2["from"]) && value["id"] < value2["id"]) {
        // Same direction
        sibling_edges.push([key2, 1]);
      }
      else if ((value["from"] == value2["to"] && value["to"] == value2["from"]) && value["id"] < value2["id"]) {
        // Opposite direction
        sibling_edges.push([key2, -1]);
      }
    }
    if (sibling_edges.length > 1) {
      to_smooth.push(sibling_edges);
    }
  }

  for (var i = 0; i < to_smooth.length; i++) {
    siblings = to_smooth[i]
    /* Determine the arc roundness depending on the number og sibling edges
    following this pattern :
    roundness = {
      2: [-0.25, 0.25],
      3: [-0.3, 0, 0.3],
      4: [-0.5, -0.25, 0.25, 0.5],
      5: [-0.6, -0.3, 0, 0.3, 0.6],
      ...
    }
    */
    if (siblings.length % 2 == 0) {
      roundness = [];
      for (var k = 1; k < siblings.length / 2 + 1; k++) {
        roundness = [-0.25 * k, ...roundness, 0.25 * k];
      }
    }
    else {
      roundness = [0];
      for (var k = 1; k < (siblings.length - 1) / 2 + 1; k++) {
        roundness = [-0.3 * k, ...roundness, 0.3 * k];
      }
    }
    for (var j = 0; j < siblings.length; j++) {
      edges[siblings[j][0]]["smooth"] = { type: 'curvedCW', roundness: roundness[j] * siblings[j][1] };
    }
  }
  return edges
}

function getAllUpstreamNodes(selectedNodes) {
  var queueArrayUpstream = [...selectedNodes];
  var totalUpstreamNodes = [...selectedNodes];

  while (queueArrayUpstream.length != 0) {
    var node_path = queueArrayUpstream.shift();
    var connectedNodes = dico_edges_children_inverted[node_path];
    if (connectedNodes != undefined) {
      for (i = 0; i < connectedNodes.length; i++) {
        if (!totalUpstreamNodes.includes(connectedNodes[i])) {
          totalUpstreamNodes.push(connectedNodes[i]);
          queueArrayUpstream.push(connectedNodes[i]);
        }
      }
    }
  }
  return totalUpstreamNodes;
}

function shortestpathEnd(selectedNode) {
  // Shortest path to the closest end node
  if (dico_nodes[selectedNode].group.includes('end')) {
    return [selectedNode];
  }

  var queueArray = [[selectedNode]];

  while (queueArray.length != 0) {
    var node_path = queueArray.shift();
    var node_last = node_path[node_path.length - 1];

    var connectedNodes = dico_edges_children[node_last];

    for (i = 0; i < connectedNodes.length; i++) {
      if (dico_nodes[connectedNodes[i]].group.includes('end')) {
        var node_path_2 = [...node_path];
        node_path_2.push(connectedNodes[i]);
        return node_path_2;
      } else {
        if (!node_path.includes(connectedNodes[i])) {
          var node_path_2 = [...node_path];
          node_path_2.push(connectedNodes[i]);
          queueArray.push(node_path_2);
        }
      }
    }
  }
  return queueArray;
}

function shortestpathToChosenEnd(selectedNode, endNode) {
  // Same as above but it gets to the chosen end node
  if (dico_nodes[selectedNode].group.includes('end')) {
    return [selectedNode];
  }

  var queueArray = [[selectedNode]];

  while (queueArray.length != 0) {
    var node_path = queueArray.shift();
    var node_last = node_path[node_path.length - 1];

    var connectedNodes = dico_edges_children[node_last];

    if (connectedNodes != undefined) {
      for (i = 0; i < connectedNodes.length; i++) {
        if (connectedNodes[i] == endNode) {
          var node_path_2 = [...node_path];
          node_path_2.push(connectedNodes[i]);
          return node_path_2;
        } else {
          if (!node_path.includes(connectedNodes[i])) {
            var node_path_2 = [...node_path];
            node_path_2.push(connectedNodes[i]);
            queueArray.push(node_path_2);
          }
        }
      }
    }
  }
  return queueArray;
}

function getAllEndNodes() {
  // Returns array with all end nodes of graph
  var ends = [];

  for (var node in dico_nodes) {
    if (dico_nodes[node].group.includes('end')) {
      ends.push(node);
    }
  }
  return ends;
}
function reachableNodesFrom(selectedNode, visited = new Set()) {
  // Get all reachable nodes from on start node
  if (visited.has(selectedNode)) return [];
  visited.add(selectedNode);

  if (dico_nodes[selectedNode].group.includes('end')) {
    return [selectedNode];
  }

  var reachableNodes = [selectedNode];
  var connectedNodes = dico_edges_children[selectedNode];
  
  for (let i = 0; i < connectedNodes.length; i++) {
    reachableNodes = reachableNodes.concat(reachableNodesFrom(connectedNodes[i], visited))
  }
  return reachableNodes;
}

function display_only_path_from_node(node_parameter) {
  // Get all nodes leading from a specific node

  allPaths = reachableNodesFrom(node_parameter);

  selected_nodes_id = [...new Set(allPaths)];

  selected_nodes = [];
  for (var i = 0; i < selected_nodes_id.length; i++) {
    selected_nodes.push(dico_nodes[selected_nodes_id[i]]);
  }

  selected_edges = [];

  for (var i = 0; i < data_edges.length; i++) {
    if (
      selected_nodes_id.includes(data_edges[i].to) &&
      selected_nodes_id.includes(data_edges[i].from)
    ) {
      selected_edges.push(data_edges[i]);
    }
  }

  return [selected_nodes, selected_edges];
}

function change_dropdown_endnodes(data_nodes) {
  // Update the end nodes dropdown with all end nodes (May need improvments with "getAllEndNodes" function)
  for (var i = 0; i < data_nodes.length; i++) {
    if (data_nodes[i].group.includes('end')) {
      var ele = document.createElement('option');
      ele.innerText = data_nodes[i].label;
      ele.value = parseInt(data_nodes[i].id);
      document.querySelector('.form-select').appendChild(ele);
    }
  }
}

const selectElement = document.querySelector('.form-select');

selectElement.addEventListener('change', (event) => {
  // Event triggered when switching end node
  selection_end_node(data_nodes);
});

function selection_end_node(data_nodes) {
  if (document.querySelector('.form-select').value == 'All End Nodes') {
    var children_array = document.querySelector('.form-select').children;
    var end_nodes = [];
    for (var i = 0; i < children_array.length; i++) {
      if (children_array[i].value != 'All End Nodes') {
        end_nodes.push(parseInt(children_array[i].value));
      }
    }
  } else {
    end_nodes = [[parseInt(document.querySelector('.form-select').value)]];
  }

  upstream_node = getAllUpstreamNodes(end_nodes);
  var data_node_2 = [];
  for (var i = 0; i < upstream_node.length; i++) {
    for (var j = 0; j < data_nodes.length; j++) {
      if (data_nodes[j].id == upstream_node[i]) {
        if (!data_node_2.includes(data_nodes[j])) {
          data_node_2.push(data_nodes[j]);
        }
      }
    }
  }
  initNetwork(data_node_2, data_edges);
  return 0;
}

function dagrePositioning(allNodes, horizontalMode) {
  if (window.computedHorizGraph && horizontalMode) {
    //restore the positions of the nodes and edges from the hidden attributes
    for (nodeId in allNodes) {
      allNodes[nodeId].x = allNodes[nodeId].hiddenx_horiz;
      allNodes[nodeId].y = allNodes[nodeId].hiddeny_horiz;
    }
    return allNodes;
  } else if (window.computedVertGraph && !horizontalMode) {
    // restore the positions of the nodes and edges from the hidden attributes
    for (nodeId in allNodes) {
      allNodes[nodeId].x = allNodes[nodeId].hiddenx_vert;
      allNodes[nodeId].y = allNodes[nodeId].hiddeny_vert;
    }
    return allNodes;
  }
  // Create a new directed graph
  var g = new dagre.graphlib.Graph();
  // Set an object for the graph label
  if (horizontalMode) {
    g.setGraph({ rankdir: 'BT', ranker: 'tight-tree' });
    var width_degre = 20;
    var height_dagre = 100;
  } else {
    g.setGraph({ rankdir: 'LR', ranker: 'tight-tree' });
    var width_degre = 250;
    var height_dagre = 20;
  }
  // Default to assigning a new object as a label for each new edge.
  g.setDefaultEdgeLabel(function () {
    return {};
  });
  for (nodeId in allNodes) {
    g.setNode(allNodes[nodeId].id, {
      label: allNodes[nodeId].label,
      width: width_degre,
      height: height_dagre,
    });
  }

  for (edgeId in allEdges) {
    g.setEdge(allEdges[edgeId].from, allEdges[edgeId].to);
  }

  dagre.layout(g);

  if (horizontalMode) {
    window.computedHorizGraph = true;

    g.nodes().forEach(function (v) {
      allNodes[v].x = g.node(v).x;
      allNodes[v].y = g.node(v).y;
      allNodes[v].hiddenx_horiz = g.node(v).x;
      allNodes[v].hiddeny_horiz = g.node(v).y;
    });
  } else {
    window.computedVertGraph = true;

    g.nodes().forEach(function (v) {
      allNodes[v].x = g.node(v).x;
      allNodes[v].y = g.node(v).y;
      allNodes[v].hiddenx_vert = g.node(v).x;
      allNodes[v].hiddeny_vert = g.node(v).y;
    });
  }

  return allNodes;
}

function displayHideText(checkbox) {
  if (checkbox.checked) {
    for (var nodeId in allNodes) {
      if (allNodes[nodeId].hiddenLabel === undefined) {
        allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
        allNodes[nodeId].label = undefined;
      }
    }
    for (var edgeId in allEdges) {
      if (
        allEdges[edgeId].hiddenLabel === undefined ||
        allEdges[edgeId].hiddenLabel === ' '
      ) {
        allEdges[edgeId].hiddenLabel = allEdges[edgeId].label;
        allEdges[edgeId].label = ' ';
      }
    }
  } else {
    for (var nodeId in network.body.nodes) {
      if (allNodes[nodeId].hiddenLabel != undefined) {
        allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
        allNodes[nodeId].hiddenLabel = undefined;
      }
    }
    for (var edgeId in allEdges) {
      if (
        allEdges[edgeId].hiddenLabel != undefined &&
        allEdges[edgeId].hiddenLabel !== ' '
      ) {
        allEdges[edgeId].label = allEdges[edgeId].hiddenLabel;
        allEdges[edgeId].hiddenLabel = undefined;
      }
    }
  }

  var updateArrayNodes = [];
  for (nodeId in allNodes) {
    if (allNodes.hasOwnProperty(nodeId)) {
      updateArrayNodes.push(allNodes[nodeId]);
    }
  }

  var updateArrayEdges = [];
  for (edgeId in allEdges) {
    if (allEdges.hasOwnProperty(edgeId)) {
      updateArrayEdges.push(allEdges[edgeId]);
    }
  }

  nodes.update(updateArrayNodes);
  edges.update(updateArrayEdges);
}

function displayHideNodes(checkbox) {
  if (checkbox.checked) {
    for (var nodeId in allNodes) {
      if (allNodes[nodeId].hiddenLabel === undefined) {
        allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
        allNodes[nodeId].label = undefined;
      }
    }
  } else {
    for (var nodeId in network.body.nodes) {
      if (allNodes[nodeId].hiddenLabel != undefined) {
        allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
        allNodes[nodeId].hiddenLabel = undefined;
      }
    }
  }
  var updateArrayNodes = [];
  for (nodeId in allNodes) {
    if (allNodes.hasOwnProperty(nodeId)) {
      updateArrayNodes.push(allNodes[nodeId]);
    }
  }
  nodes.update(updateArrayNodes);
}

function displayHideEdges(checkbox) {
  if (checkbox.checked) {
    for (var edgeId in allEdges) {
      if (
        allEdges[edgeId].hiddenLabel === undefined ||
        allEdges[edgeId].hiddenLabel === ' '
      ) {
        allEdges[edgeId].hiddenLabel = allEdges[edgeId].label;
        allEdges[edgeId].label = ' ';
      }
    }
  } else {
    for (var edgeId in allEdges) {
      if (
        allEdges[edgeId].hiddenLabel != undefined &&
        allEdges[edgeId].hiddenLabel !== ' '
      ) {
        allEdges[edgeId].label = allEdges[edgeId].hiddenLabel;
        allEdges[edgeId].hiddenLabel = undefined;
      }
    }
  }

  var updateArrayEdges = [];
  for (edgeId in allEdges) {
    if (allEdges.hasOwnProperty(edgeId)) {
      updateArrayEdges.push(allEdges[edgeId]);
    }
  }
  edges.update(updateArrayEdges);
}

function horizontalGraph() {
  nodes_positioning();
  network.redraw();
  network.fit();
}

function nodes_positioning() {
  allNodes = dagrePositioning(
    allNodes,
    document.getElementById('switchHorizontalGraph').checked,
  );
  var updateArrayNodes = [];
  for (nodeId in allNodes) {
    if (allNodes.hasOwnProperty(nodeId)) {
      updateArrayNodes.push(allNodes[nodeId]);
    }
  }
  nodes.update(updateArrayNodes);
}

function percentage_path_passing_through_nodes() {
  var nodesDico = {};
  var number_node = 0;

  // initialization
  for (var nodeId in allNodes) {
    nodesDico[nodeId] = 0;
    number_node += 1;
  }

  var list_cluster_id = [];
  var list_cluster_all_id = []; // cluster nodes + their children

  for (var node in nodesDico) {
    if (network.getConnectedNodes(node, 'from').length > 10) {
      list_cluster_id.push(parseInt(node));
    }
  }

  // number of paths for each node
  for (var nodeId in allNodes) {
    if (!allNodes[nodeId].group.includes('end')) {
      var path_to_highlight = pathHighlight(nodeId);
      for (i = 0; i < path_to_highlight.length; i++) {
        nodesDico[path_to_highlight[i]] = nodesDico[path_to_highlight[i]] + 1;
      }

      var node_in_cluster_bool = false;
      for (var i = 0; i < list_cluster_id.length; i++) {
        if (path_to_highlight.includes(parseInt(list_cluster_id[i]))) {
          node_in_cluster_bool = true;
        }
      }

      if (node_in_cluster_bool == true) {
        list_cluster_all_id.push(parseInt(nodeId));
      }
    }
  }

  // calculation of percentages
  var list_end_nodes = [];
  var depth_percentage = 15;

  var dico_rank_nodes = {};

  var lowest_ranked_node_list = [];

  for (var nodeId in allNodes) {
    if (allNodes[nodeId].group.includes('end')) {
      list_end_nodes.push(nodeId);
      allNodes[nodeId].level = 0;
    }
  }

  for (i = 0; i < depth_percentage; i++) {
    dico_rank_nodes[i] = [];
  }

  for (i = 0; i < list_end_nodes.length; i++) {
    dico_rank_nodes[0] = dico_rank_nodes[0]
      .concat(network.getConnectedNodes(list_end_nodes[i], 'from'))
      .filter((x) => !list_end_nodes.includes(x));
  }

  lowest_ranked_node_list = list_end_nodes;

  function htmlTitle(html) {
    const container = document.createElement('div');
    container.innerHTML = html;
    return container;
  }

  for (rank_node = 1; rank_node < depth_percentage; rank_node++) {
    for (i = 0; i < dico_rank_nodes[rank_node - 1].length; i++) {
      var string_tooltip =
        (
          (nodesDico[dico_rank_nodes[rank_node - 1][i]] /
            (number_node - lowest_ranked_node_list.length)) *
          100
        ).toFixed(1) +
        '% (rank node : ' +
        rank_node +
        ')';

      allNodes[dico_rank_nodes[rank_node - 1][i]].level = rank_node;

      allNodes[dico_rank_nodes[rank_node - 1][i]].title = htmlTitle(
        "<span style='width: 180px;background-color: black;color: #fff;text-align: center;padding: 5px 0;border-radius: 6px;position: absolute;'>" +
        string_tooltip +
        '</span>',
      );

      dico_rank_nodes[rank_node] = dico_rank_nodes[rank_node]
        .concat(
          network.getConnectedNodes(dico_rank_nodes[rank_node - 1][i], 'from'),
        )
        .filter(
          (x) =>
            !lowest_ranked_node_list
              .concat(dico_rank_nodes[rank_node - 1])
              .includes(x),
        );
    }

    lowest_ranked_node_list = lowest_ranked_node_list.concat(
      dico_rank_nodes[rank_node - 1],
    );
    lowest_ranked_node_list = [...new Set(lowest_ranked_node_list)];
  }

  // transform the object into an array
  var updateArrayNodes = [];
  for (nodeId in allNodes) {
    if (allNodes.hasOwnProperty(nodeId)) {
      updateArrayNodes.push(allNodes[nodeId]);
    }
  }
  var updateArrayEdges = [];
  for (edgeId in allEdges) {
    if (allEdges.hasOwnProperty(edgeId)) {
      updateArrayEdges.push(allEdges[edgeId]);
    }
  }
  nodes.update(updateArrayNodes);

  return [nodesDico, list_cluster_id, list_cluster_all_id, dico_rank_nodes];
}

function pathHighlight(selectedNode) {
  if (allNodes[selectedNode].group.includes('end')) {
    return [selectedNode];
  }

  var queueArray = [[selectedNode]];

  while (queueArray.length != 0) {
    var node_path = queueArray.shift();
    var node_last = node_path[node_path.length - 1];

    var connectedNodes = network.getConnectedNodes(node_last, 'to');

    for (i = 0; i < connectedNodes.length; i++) {
      if (allNodes[connectedNodes[i]].group.includes('end')) {
        var node_path_2 = [...node_path];
        node_path_2.push(connectedNodes[i]);
        return node_path_2;
      } else {
        if (!node_path.includes(connectedNodes[i])) {
          var node_path_2 = [...node_path];
          node_path_2.push(connectedNodes[i]);
          queueArray.push(node_path_2);
        }
      }
    }
  }
  return queueArray;
}

function neighbourhoodHighlight(params) {
  // if something is selected:
  if (params.nodes.length > 0) {
    highlightActive = true;
    var i, j;
    var selectedNode = params.nodes[0];
    var degrees = 2;

    var path_to_highlight = pathHighlight(params.nodes[0]);

    // mark all nodes as hard to read.
    // for (var k in allNodes) {
    //     if (!allNodes[k].group.includes("end")) {
    //         allNodes[k].group = allNodes[k].group + "_transparent";
    //     }
    // }

    for (var nodeId in allNodes) {
      if (allNodes[nodeId].hiddenLabel === undefined) {
        allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
        allNodes[nodeId].label = undefined;
      }
    }

    for (var edgeId in allEdges) {
      if (
        allEdges[edgeId].hiddenLabel === undefined ||
        allEdges[edgeId].hiddenLabel === ' '
      ) {
        allEdges[edgeId].hiddenLabel = allEdges[edgeId].label;
        allEdges[edgeId].label = ' ';
      }
    }

    // display path
    for (i = 0; i < path_to_highlight.length; i++) {
      // if (!allNodes[path_to_highlight[i]].group.includes("end")) {
      //     allNodes[path_to_highlight[i]].group = allNodes[path_to_highlight[i]].group.split('_transparent')[0];
      // }

      if (allNodes[path_to_highlight[i]].hiddenLabel !== undefined) {
        allNodes[path_to_highlight[i]].label =
          allNodes[path_to_highlight[i]].hiddenLabel;
        allNodes[path_to_highlight[i]].hiddenLabel = undefined;
      }
    }

    for (var edgeId in allEdges) {
      allEdges[edgeId].background = { enabled: false };
      if (taggedEdges.includes(edgeId)) {
        allEdges[edgeId].color = 'rgba(102, 0, 204, 0.15)';
      }
      else {
        allEdges[edgeId].color = 'rgba(77,77,77,0.15)';
      }
      for (j = 0; j < path_to_highlight.length - 1; j++) {
        if (
          allEdges[edgeId].from == path_to_highlight[j] &&
          allEdges[edgeId].to == path_to_highlight[j + 1]
        ) {
          allEdges[edgeId].background = {
            size: 10,
            enabled: true,
            color: 'rgba(0, 176, 255,1)',
          };
          // Check if link between two different domains
          if (taggedEdges.includes(edgeId)) {
            allEdges[edgeId].color = 'rgba(102, 0, 204, 1)';
          }
          else {
            allEdges[edgeId].color = 'rgba(77,77,77,1)';
          }

          if (
            allEdges[edgeId].hiddenLabel !== undefined &&
            allEdges[edgeId].hiddenLabel != ' '
          ) {
            allEdges[edgeId].label = allEdges[edgeId].hiddenLabel;
            allEdges[edgeId].hiddenLabel = undefined;
          }
        }
      }
    }

    last_path = path_to_highlight;
    if ($('.modal')[0].style.display == 'block') {
      displayPathGraph(path_to_highlight);
    }

    var connectedNodes = network.getConnectedNodes(selectedNode);

    // all first degree nodes get their own color and their label back
    for (i = 0; i < connectedNodes.length; i++) {
      // if (!allNodes[connectedNodes[i]].group.includes("end")) {
      //     allNodes[connectedNodes[i]].group = allNodes[connectedNodes[i]].group.split('_transparent')[0];
      // }

      if (allNodes[connectedNodes[i]].hiddenLabel !== undefined) {
        allNodes[connectedNodes[i]].label =
          allNodes[connectedNodes[i]].hiddenLabel;
        allNodes[connectedNodes[i]].hiddenLabel = undefined;
      }
    }

    // the main node gets its own color and its label back.
    // if (!allNodes[selectedNode].group.includes("end")) {
    //     allNodes[selectedNode].group = allNodes[selectedNode].group.split('_transparent')[0];
    // }

    if (allNodes[selectedNode].hiddenLabel !== undefined) {
      allNodes[selectedNode].label = allNodes[selectedNode].hiddenLabel;
      allNodes[selectedNode].hiddenLabel = undefined;
    }
  } else if (highlightActive === true) {
    // reset all nodes
    hiddenCheckbox = document.getElementById('switchHideText');
    if (hiddenCheckbox.checked) {
      // hide the label of the selected nodes
      for (var nodeId in allNodes) {
        // if (!allNodes[nodeId].group.includes("end")) {
        //     allNodes[nodeId].group = allNodes[nodeId].group.split('_transparent')[0];
        // }
        if (allNodes[nodeId].label !== undefined) {
          allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
          allNodes[nodeId].label = undefined;
        }
      }
      highlightActive = false;

      for (var edgeId in allEdges) {
        allEdges[edgeId].background = { enabled: false };
        // Check if link between two different domains
        if (taggedEdges.includes(edgeId)) {
          allEdges[edgeId].color = 'rgba(102, 0, 204, 1)';
        }
        else {
          allEdges[edgeId].color = 'rgba(77,77,77,1)';
        }

        if (
          allEdges[edgeId].label !== undefined &&
          allEdges[edgeId].label !== ' '
        ) {
          allEdges[edgeId].hiddenLabel = allEdges[edgeId].label;
          allEdges[edgeId].label = ' ';
        }
      }
    } else {
      for (var nodeId in allNodes) {
        // if (!allNodes[nodeId].group.includes("end")) {
        //     allNodes[nodeId].group = allNodes[nodeId].group.split('_transparent')[0];
        // }
        if (allNodes[nodeId].hiddenLabel !== undefined) {
          allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
          allNodes[nodeId].hiddenLabel = undefined;
        }
      }
      highlightActive = false;

      for (var edgeId in allEdges) {
        allEdges[edgeId].background = { enabled: false };
        // Check if link between two different domains
        if (taggedEdges.includes(edgeId)) {
          allEdges[edgeId].color = 'rgba(102, 0, 204, 1)';
        }
        else {
          allEdges[edgeId].color = 'rgba(77,77,77,1)';
        }

        if (
          allEdges[edgeId].hiddenLabel !== undefined &&
          allEdges[edgeId].hiddenLabel !== ' '
        ) {
          allEdges[edgeId].label = allEdges[edgeId].hiddenLabel;
          allEdges[edgeId].hiddenLabel = undefined;
        }
      }
    }
  } else {
    return;
  }
  // transform the object into an array
  var updateArrayNodes = [];
  for (nodeId in allNodes) {
    if (allNodes.hasOwnProperty(nodeId)) {
      updateArrayNodes.push(allNodes[nodeId]);
    }
  }

  var updateArrayEdges = [];
  for (edgeId in allEdges) {
    if (allEdges.hasOwnProperty(edgeId)) {
      updateArrayEdges.push(allEdges[edgeId]);
    }
  }

  nodes.update(updateArrayNodes);
  edges.update(updateArrayEdges);
}

// Write a function called displayPathGraph that takes in a path as an argument, and creates a vis network representing the path.
function displayPathGraph(path) {
  var pathNodes = [];
  var pathEdges = [];

  for (var i = 0; i < path.length; i++) {
    pathNodes.push({ ...allNodes[path[i]] });
  }

  for (var edgeId in allEdges) {
    for (var i = 0; i < path.length; i++) {
      if (
        allEdges[edgeId].from == path[i] &&
        allEdges[edgeId].to == path[i + 1]
      ) {
        pathEdges.push({ ...allEdges[edgeId] });
      }
    }
  }

  var pathContainer = document.getElementById('pathnetwork');
  $('.modal')[0].style.display = 'block';

  for (nodeId in pathNodes) {
    // set coordinates of nodes so that they are in a line
    pathNodes[nodeId].x = 300 * nodeId;
    pathNodes[nodeId].y = 50 * (nodeId % 2);
    // pathNodes[nodeId].y = 0;
  }

  var pathData = {
    nodes: pathNodes,
    edges: pathEdges,
  };

  var pathNetwork = new vis.Network(pathContainer, pathData, options);

  pathNetwork.fit();
}

// changeNodeSize(), hexToRgb(), clusterNodes() and update_graph() :

//     function changeNodeSize(min, max) {
//         let dict = {};
//         for (var id in allNodes) {
//             dict[id] = network.getConnectedNodes(id).length;
//         }

//         let arr = Object.values(dict);

//         let max_edges = Math.max(...arr);
//         let min_edges = Math.min(...arr);

//         let diff = max_edges - min_edges;
//         if (diff == 0) {
//             Object.keys(dict).forEach(function(id) {
//             network.body.nodes[id].options.icon.size = min;
//             });
//         } else {
//             Object.keys(dict).forEach(function(id) {
//             let scaling = (dict[id] - min_edges)/diff;
//             let size = min + scaling*(max - min);
//             network.body.nodes[id].options.icon.size = size;
//             });
//         }
//     }

//     network.once("stabilizationIterationsDone", function () {
//     network.setOptions({
//         nodes: {physics: false},
//         edges: {physics: false},
//     });
//     document.getElementById("loadingBox").style.display = 'none';
//     });

//     network.on("selectNode", function (params) {
//     if (params.nodes.length == 1) {
//       if (network.isCluster(params.nodes[0]) == true) {
//         network.openCluster(params.nodes[0]);
//       }
//     }
//   });

//       //update_graph(allNodes,allEdges);
//     return [network, allNodes, allEdges]
//     }

// function clusterNodes() {
// // First we get the nodes with more than 30 connections

// let dict = {};
// for (var id in allNodes) {
//     dict[id] = network.getConnectedNodes(id).length;
// }

// var sorted = Object.keys(dict).map(function(key) {
//   return [key, dict[key]];
// });

// // Sort the array based on the second element
// sorted.sort(function(first, second) {
//   return second[1] - first[1];
// });

// sorted.every(tuple => { // TODO : improve this
//     if (tuple[1] < 30) {
//         return false;
//     }
//     // clusterNode(tuple[0], true);
//     clusterChildren(tuple[0]);
//     return true;
// });

// }

// function hexToRgb(hex) {
// var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
// return result ? {
//     r: parseInt(result[1], 16),
//     g: parseInt(result[2], 16),
//     b: parseInt(result[3], 16)
// } : null;
// }
// function update_graph(nodes_list, edges_list) {
// //console.log("Called update_graph");

// for (var nodeId in nodes_list) {
//     var existing_color = network.body.nodes[nodeId].options.icon.color.split(',');
//     var new_color = "".concat("rgba(", existing_color[0].split("(")[1], ",", existing_color[1], ",", existing_color[2], ",")

//     if (network.body.nodes[nodeId].options["isDisplayed"] == false) {
//         new_color = new_color.concat("0)");
//         network.body.nodes[nodeId].options.icon.color=new_color;
//         network.body.nodes[nodeId].options.hiddenLabel = network.body.nodes[nodeId].options.label;
//         network.body.nodes[nodeId].options.label = undefined;
//     }
//     else if (network.body.nodes[nodeId].options["isCluster"] == true) {
//         network.body.nodes[nodeId].options.icon.color="rgba(255,165,0,1)"
//         new_color = new_color.concat("1)");
//         network.body.nodes[nodeId].options.icon.hiddenColor = new_color;
//     }
//     else {
//         if (network.body.nodes[nodeId].options.icon.hiddenColor != undefined) {
//             new_color = network.body.nodes[nodeId].options.icon.hiddenColor;
//             network.body.nodes[nodeId].options.icon.color = new_color;
//             network.body.nodes[nodeId].options.icon.hiddenColor = undefined;
//             network.body.nodes[nodeId].options.label = network.body.nodes[nodeId].options.hiddenLabel;
//             network.body.nodes[nodeId].options.hiddenLabel = undefined;
//         }
//         else {
//             new_color = new_color.concat("1)");
//             network.body.nodes[nodeId].options.icon.color=new_color;
//         }
//     }
// }
// for (var edgeId in edges_list) {
//     if (network.body.edges[edgeId].options.color.color.includes("#")) {
//         var existing_color = hexToRgb(network.body.edges[edgeId].options.color.color);
//         var new_color = "".concat("rgba(",existing_color.r, ",", existing_color.g, ",", existing_color.b, ",")
//     }
//     else {
//         var existing_color = network.body.edges[edgeId].options.color.color.split(',');
//         var new_color = "".concat("rgba(", existing_color[0].split("(")[1], ",", existing_color[1], ",", existing_color[2], ",")
//     }

//     if (network.body.nodes[edges_list[edgeId].from].options["isDisplayed"]== false || network.body.nodes[edges_list[edgeId].to].options["isDisplayed"] == false) {
//     // if (nodes_list[edges_list[edgeId].from].isDisplayed == false || nodes_list[edges_list[edgeId].to].isDisplayed == false) {
//         new_color = new_color.concat("0)");
//         network.body.edges[edgeId].options.color.color=new_color;
//         network.body.edges[edgeId].options.hiddenLabel = network.body.edges[edgeId].options.label;
//         network.body.edges[edgeId].options.label = ' ';
//     }
//     else {
//         new_color = new_color.concat("1)");
//         network.body.edges[edgeId].options.color.color=new_color;
//         if (network.body.edges[edgeId].options.hiddenLabel != ' ') {
//             network.body.edges[edgeId].options.label = network.body.edges[edgeId].options.hiddenLabel;
//             network.body.edges[edgeId].options.hiddenLabel = ' ';
//         }
//     }
// }
// network.redraw()
// }

// Mark all nodes with more than 'threshold' incoming connections
function markClusters(threshold) {
  let dict = {};
  for (var nodeId in allNodescopy) {
    dict[nodeId] = incomingNodes(nodeId, edgesdeepcopy).length;
  }
  var sorted = Object.keys(dict).map(function (key) {
    return [key, dict[key]];
  });

  // Sort the array based on the second element
  sorted.sort(function (first, second) {
    return second[1] - first[1];
  });
  sorted.every((tuple) => {
    // TODO : improve this
    if (tuple[1] < threshold) {
      return false;
    }
    // console.log("Decided to cluster node ", tuple[0], tuple[1]);
    markClusterComplete(tuple[0]);
    return true;
  });
}

function markClustersPartial(threshold) {
  for (var nodeId in allNodescopy) {
    var group = allNodescopy[nodeId].group.split('_')[0];
    if (group == 'start' || group == 'end' || group == 'cluster') {
      continue;
    }

    if (
      allNodescopy[nodeId].clusterType == 'complete' ||
      allNodescopy[nodeId].clusterType == 'partial'
    ) {
      continue;
    }

    var clusterChildren = [];
    incomingNodes(nodeId, edgesdeepcopy).forEach((node) => {
      var incomingEdgesNb = incomingNodes(node, edgesdeepcopy).length;
      if (incomingEdgesNb > 0) {
        // Only cluster nodes that don't have children
        return;
      }
      if (
        allNodescopy[node] != undefined &&
        (allNodescopy[node].group.includes('User') ||
          allNodescopy[node].group.includes('Computer') ||
          allNodescopy[node].group.includes('Group'))
      ) {
        clusterChildren.push(node);
      }
    });

    if (clusterChildren.length > threshold) {
      // console.log("clustering", nodeId)
      markClusterPartial(nodeId, threshold);
    }
  }
}

// Special type of cluster : only for end nodes
function markClustersForward(threshold) {
  for (var nodeId in allNodescopy) {
    if (outgoingNodes(nodeId, edgesdeepcopy).length == 0) {
      // console.log(nodeId, " no outgoing edges")
      continue;
    }

    var clusterChildren = [];
    outgoingNodes(nodeId, edgesdeepcopy).forEach((node) => {
      var outgoingEdgesNb = outgoingNodes(node, edgesdeepcopy).length;
      if (outgoingEdgesNb > 0) {
        // Only cluster nodes that are end nodes
        return;
      }

      if (
        allNodescopy[node] != undefined &&
        !allNodescopy[node].group.includes('end')
      ) {
        //console.log("ignoring", nodeId, " is not an end node");
        return;
      }
      if (node in allNodescopy) {

        if (allNodescopy[node].group.includes('Group')) {
          return;
        }
      }

      clusterChildren.push(node);
    });

    if (clusterChildren.length >= threshold) {
      // Forward cluster takes priority over other clusters
      if (
        allNodescopy[nodeId].clusterType == 'complete' ||
        allNodescopy[nodeId].clusterType == 'partial'
      ) {
        console.log(
          'overriding',
          allNodescopy[nodeId].clusterType + ' for ',
          nodeId,
        );
        unmarkCluster(nodeId);
      }
      // console.log("deciding to cluster", nodeId);
      allClusters[nodeId] = clusterChildren;

      allNodescopy[nodeId].clusterType = 'forward';
      allNodescopy[nodeId].hiddenGroup = allNodescopy[nodeId].group; // TODO set an appropriate icon for clusters
      //allNodescopy[nodeId].group = "cluster_Group"; // TODO set an appropriate icon for clusters
      allNodescopy[nodeId].clusterChildren = clusterChildren; // TODO set an appropriate icon for clusters
      allNodescopy[nodeId].image = url_cluster(
        'Group_cluster',
        'rgba(252,147,3,1)',
        allNodescopy[nodeId].clusterChildren.length,
      );
      allNodescopy[nodeId].size = 40;
    }
  }
}
// Mark specific cluster
function markClusterComplete(nodeId) {
  if (typeof allNodescopy[nodeId].unClusterable !== 'undefined') {
    printRecurseWarning(
      (typeof allNodescopy[nodeId].label !== 'undefined' &&
        allNodescopy[nodeId].label) ||
      allNodescopy[nodeId].hiddenLabel,
    );
    return;
  }

  var clusterChildren = [];
  try {
    clusterChildren = clusterChildren.concat(getChildren(nodeId));
  } catch (error) {
    // In case of recursion error
    printRecurseWarning(
      (typeof allNodescopy[nodeId].label !== 'undefined' &&
        allNodescopy[nodeId].label) ||
      allNodescopy[nodeId].hiddenLabel,
    );
    markUnclusterable(nodeId);
    return;
  }
  allClusters[nodeId] = clusterChildren;

  // console.log("marking cluster complete", nodeId)
  allNodescopy[nodeId].clusterType = 'complete';

  allNodescopy[nodeId].hiddenGroup = allNodescopy[nodeId].group; // TODO set an appropriate icon for clusters
  allNodescopy[nodeId].clusterChildren = clusterChildren; // TODO set an appropriate icon for clusters

  allNodescopy[nodeId].image = url_cluster(
    'Group_cluster',
    'rgba(252,147,3,1)',
    getChildren(nodeId, edgesdeepcopy).length,
  );
  allNodescopy[nodeId].size = 40;
}

function markClusterPartial(nodeId, threshold) {
  if (incomingNodes(nodeId).length == 0) {
    return;
  }

  var clusterChildren = [];
  incomingNodes(nodeId, edgesdeepcopy).forEach((node) => {
    var incomingEdgesNb = incomingNodes(node, edgesdeepcopy).length;
    if (incomingEdgesNb > 0) {
      // Only cluster nodes that don't have children
      return;
    }
    clusterChildren.push(node);
  });
  // console.log(clusterChildren);
  if (clusterChildren.length >= threshold) {
    allClusters[nodeId] = clusterChildren;

    allNodescopy[nodeId].clusterType = 'partial';
    allNodescopy[nodeId].hiddenGroup = allNodescopy[nodeId].group; // TODO set an appropriate icon for clusters
    // allNodescopy[nodeId].group = "cluster_Group"; // TODO set an appropriate icon for clusters
    allNodescopy[nodeId].clusterChildren = clusterChildren; // TODO set an appropriate icon for clusters

    allNodescopy[nodeId].image = url_cluster(
      'Group_cluster',
      'rgba(252,147,3,1)',
      allNodescopy[nodeId].clusterChildren.length,
    );
    allNodescopy[nodeId].size = 40;
  }
}

// Special type of cluster : only for end nodes
function markClusterForward(nodeId, threshold) {
  if (outgoingNodes(nodeId, edgesdeepcopy).length == 0) {
    // console.log(nodeId, " no outgoing edges")
    return;
  }

  var clusterChildren = [];
  outgoingNodes(nodeId, edgesdeepcopy).forEach((node) => {
    var outgoingEdgesNb = outgoingNodes(node, edgesdeepcopy).length;
    if (outgoingEdgesNb > 0) {
      // Only cluster nodes that are end nodes
      return;
    }

    if (!allNodescopy[node].group.includes('end')) {
      return;
    }

    if (allNodescopy[node].group.includes('Group')) {
      return;
    }

    clusterChildren.push(node);
  });

  if (clusterChildren.length >= threshold) {
    // Forward cluster takes priority over other clusters
    if (
      allNodescopy[nodeId].clusterType == 'complete' ||
      allNodescopy[nodeId].clusterType == 'partial'
    ) {
      console.log(
        'overriding',
        allNodescopy[nodeId].clusterType + ' for ',
        nodeId,
      );
      unmarkCluster(nodeId);
    }
    allClusters[nodeId] = clusterChildren;

    // console.log("deciding to cluster", allNodescopy[nodeId].hiddenLabel)
    allNodescopy[nodeId].clusterType = 'forward';
    allNodescopy[nodeId].hiddenGroup = allNodescopy[nodeId].group; // TODO set an appropriate icon for clusters
    //allNodescopy[nodeId].group = "cluster_Group"; // TODO set an appropriate icon for clusters
    allNodescopy[nodeId].clusterChildren = clusterChildren; // TODO set an appropriate icon for clusters
    allNodescopy[nodeId].image = url_cluster(
      'Group_cluster',
      'rgba(252,147,3,1)',
      allNodescopy[nodeId].clusterChildren.length,
    );
    allNodescopy[nodeId].size = 40;
  }
}
// Unmark specific cluster
function unmarkCluster(nodeId) {
  var group = allNodescopy[nodeId].group.split('_')[0];

  delete allClusters[nodeId];

  allNodescopy[nodeId].clusterType = 'none';
  allNodescopy[nodeId].group = allNodescopy[nodeId].hiddenGroup;
  allNodescopy[nodeId].image =
    icon_group_options[allNodescopy[nodeId].group]['image'];
  allNodescopy[nodeId].size = 20;
}

function markUnclusterable(nodeId) {
  allNodescopy[nodeId].unClusterable = true;
}

// Get incoming nodes (on first run, we build the cacheIncoming global variable to greatly speed up the other calls)
function incomingNodes(nodeId, edgescopy) {
  if (typeof cacheIncoming !== 'undefined') {
    if (cacheIncoming[nodeId] === undefined) {
      return [];
    }
    return cacheIncoming[nodeId];
  }
  // On the first run only, go through all edges and build the cacheIncoming global variable
  cacheIncoming = {};
  var edgesStub = edgescopy.get({ returnType: 'Object' });
  for (var edgeId in edgesStub) {
    if (typeof cacheIncoming[edgesStub[edgeId].to] == 'undefined') {
      cacheIncoming[edgesStub[edgeId].to] = [];
    }
    cacheIncoming[edgesStub[edgeId].to].push(edgesStub[edgeId].from);
    // console.log(cacheIncoming)
  }
  if (cacheIncoming[nodeId] === undefined) {
    return [];
  }
  return cacheIncoming[nodeId];
}

function outgoingNodes(nodeId, edgescopy) {
  if (typeof cacheOutgoing !== 'undefined') {
    if (cacheOutgoing[nodeId] === undefined) {
      return [];
    }
    return cacheOutgoing[nodeId];
  }
  // On the first run only, go through all edges and build the cacheOutgoing global variable
  cacheOutgoing = {};
  var edgesStub = edgescopy.get({ returnType: 'Object' });
  for (var edgeId in edgesStub) {
    if (typeof cacheOutgoing[edgesStub[edgeId].from] == 'undefined') {
      cacheOutgoing[edgesStub[edgeId].from] = [];
    }
    cacheOutgoing[edgesStub[edgeId].from].push(edgesStub[edgeId].to);
    // console.log(cacheOutgoing)
  }
  if (cacheOutgoing[nodeId] === undefined) {
    return [];
  }
  return cacheOutgoing[nodeId];
}

// Recursively get all incoming nodes (children)
function getChildren(nodeId) {
  var children = incomingNodes(nodeId, edgesdeepcopy);
  if (children.length > 0) {
    children.forEach((child) => {
      children = children.concat(getChildren(child));
    });
  }
  return children;
}

// Create a subnetwork, that represents what should be rendered
function getSubnet() {
  var tmpedges = edgesdeepcopy.get({ returnType: 'Object' });
  var tmpnodes = nodesdeepcopy.get({ returnType: 'Object' });

  var nodesToRemove = [];
  for (var nodeId in tmpnodes) {
    if (
      tmpnodes[nodeId].clusterType == 'complete' ||
      tmpnodes[nodeId].clusterType == 'partial' ||
      tmpnodes[nodeId].clusterType == 'forward'
    ) {
      nodesToRemove = nodesToRemove.concat(tmpnodes[nodeId].clusterChildren);
    }
  }

  nodesToRemove.every((nodeId) => {
    delete tmpnodes[nodeId];
    return true;
  });

  for (edgeId in tmpedges) {
    if (
      nodesToRemove.includes(tmpedges[edgeId].from) ||
      nodesToRemove.includes(tmpedges[edgeId].to)
    ) {
      delete tmpedges[edgeId];
    }
  }
  return [tmpnodes, tmpedges];
}

function openCluster(nodeId) {
  // Remove context menu
  if (typeof ctxmenu !== 'undefined') {
    ctxmenu.outerHTML = '';
  }

  if (allNodescopy[nodeId].clusterChildren.length > 30) {
    if (
      confirm(
        'This cluster contains ' +
        allNodescopy[nodeId].clusterChildren.length +
        ' nodes, do you want to open it anyway?',
      )
    ) {
      unmarkCluster(nodeId);
      window.computedHorizGraph = false;
      window.computedVertGraph = false;
      // updateGraph({"context": "open_cluster", "nodeId": nodeId});
      updateGraph(nodeId);
      return;
    } else {
      return;
    }
  }
  unmarkCluster(nodeId);
  window.computedHorizGraph = false;
  window.computedVertGraph = false;
  // updateGraph({"context": "open_cluster", "nodeId": nodeId});
  updateGraph(nodeId);
}

function closeClusterComplete(nodeId) {
  // Remove context menu
  if (typeof ctxmenu !== 'undefined') {
    ctxmenu.outerHTML = '';
  }
  if (incomingNodes(nodeId, edgesdeepcopy).length == 0) {
    return;
  }

  markClusterComplete(nodeId);
  window.computedHorizGraph = false;
  window.computedVertGraph = false;
  // updateGraph({"context": "close_cluster", "nodeId": nodeId});
  updateGraph(nodeId);
}

function closeClusterPartial(nodeId) {
  // Remove context menu
  if (typeof ctxmenu !== 'undefined') {
    ctxmenu.outerHTML = '';
  }
  markClusterPartial(nodeId, 1);
  window.computedHorizGraph = false;
  window.computedVertGraph = false;
  // updateGraph({"context": "close_cluster", "nodeId": nodeId});
  updateGraph(nodeId);
}

function closeClusterForward(nodeId) {
  // Remove context menu
  if (typeof ctxmenu !== 'undefined') {
    ctxmenu.outerHTML = '';
  }
  markClusterForward(nodeId, 1);
  window.computedHorizGraph = false;
  window.computedVertGraph = false;
  // updateGraph({"context": "close_cluster", "nodeId": nodeId});
  updateGraph(nodeId);
}

function newThreshold(value) {
  for (let id in allNodes) {
    if (allNodes[id].clusterChildren != undefined) {
      if (allNodes[id].clusterChildren.length < value) {
        openCluster(id);
      } else {
        closeClusterForward(id);
        closeClusterPartial(id);
      }
    }
  }
}

function searchNode(string) {
  if (typeof searchbarResults !== 'undefined') {
    // Remove bar if it already exists
    searchbarResults.remove();
  }

  // Create bar
  searchbarResults = document.createElement('div');
  searchbarResults.classList.add('list-group');
  searchbarResults.id = 'searchbarResults';
  searchbarResults.style = `opacity:0.9;margin-left:${document.getElementById('search-bar-list-group').offsetLeft
    }px;position:absolute;top:${document.getElementById('search-bar-list-group').offsetTop +
    document.getElementById('search-bar-list-group').offsetHeight
    }px;`;

  for (node in allNodescopy) {
    if (typeof allNodes[node] !== 'undefined') {
      // If node is in the current graph
      var label =
        typeof allNodescopy[node].label !== 'undefined'
          ? allNodescopy[node].label
          : allNodescopy[node].hiddenLabel;
      if (label.includes(string.toUpperCase())) {
        // var opts = {
        //     position: {x:allNodes[node].x,y:allNodes[node].y },
        //     animation: {duration:250, easingFunction:"easeInOutQuad"},
        // };

        // var result = createElementFromHTML(`<a class='list-group-item list-group-item-action' onclick=network.moveTo(` + JSON.stringify(opts) + `);neighbourhoodHighlight({"nodes":[` + node +`]});>` + label + `</a>`);
        var result = createElementFromHTML(
          `<a class='list-group-item list-group-item-action' onclick=network.focus(` +
          node +
          `);neighbourhoodHighlight({"nodes":[` +
          node +
          `]});>` +
          label +
          `</a>`,
        );
        searchbarResults.appendChild(result);
      }
    } else {
      // If node is in the unclustered graph
      var label =
        typeof allNodescopy[node].label !== 'undefined'
          ? allNodescopy[node].label
          : allNodescopy[node].hiddenLabel;
      if (label.includes(string.toUpperCase())) {
        // var opts = {
        //     position: {x:allNodes[findParentCluster(node)].x,y:allNodes[findParentCluster(node)].y },
        //     animation: {duration:250, easingFunction:"easeInOutQuad"},
        // };

        var result = createElementFromHTML(
          `<a class='list-group-item list-group-item-action' onclick=network.focus(findParentCluster(` +
          node +
          `));neighbourhoodHighlight({"nodes":[findParentCluster(` +
          node +
          `)]});>` +
          label +
          ` (in a cluster)</a>`,
        );
        // var result = createElementFromHTML(`<a class='list-group-item list-group-item-action' onclick=network.moveTo(` + JSON.stringify(opts) + `);neighbourhoodHighlight({"nodes":[findParentCluster(`+ node + `)]});>` + label + ` (in a cluster)</a>`)
        searchbarResults.appendChild(result);
      }
    }
  }
  // Display bar
  document.body.appendChild(searchbarResults);
}

function findParentCluster(nodeId) {
  for (cluster in allClusters) {
    if (allClusters[cluster].includes(nodeId)) {
      return findParentCluster(cluster);
    }
  }
  return nodeId;
}

// Right click context menu logic
function bindRightClick() {
  if (document.addEventListener) {
    network.on('oncontext', function (params) {
      // Right click
      lastSelectedNode = network.getNodeAt(params.pointer.DOM);

      var e = window.event;
      e.preventDefault();

      // Remove any other context menu
      if (typeof ctxmenu !== 'undefined') {
        ctxmenu.remove();
      }

      // Create context menu at mouse position
      let menu = document.createElement('div');
      menu.id = 'ctxmenu';
      menu.style = `top:${e.pageY}px;left:${e.pageX}px`;

      if (lastSelectedNode == undefined) {
        menu.innerHTML = `<div class="list-group">
                <a class='list-group-item list-group-item-action disabled'>No Action</a>
                </div>`;
      } else {
        if (
          allNodescopy[lastSelectedNode].clusterType == 'complete' ||
          allNodescopy[lastSelectedNode].clusterType == 'partial' ||
          allNodescopy[lastSelectedNode].clusterType == 'forward'
        ) {
          menu.innerHTML =
            `<div class="list-group">
                    <a class='list-group-item list-group-item-action' onclick=openCluster(` +
            lastSelectedNode +
            `)>Open Cluster</a>
                    </div>`;
        } else {
          menu.innerHTML =
            `<div class="list-group">
                    <a class='list-group-item list-group-item-action' onclick=closeClusterComplete(` +
            lastSelectedNode +
            `)>Cluster</a>
                    <a class='list-group-item list-group-item-action' onclick=closeClusterPartial(` +
            lastSelectedNode +
            `)>Cluster direct children only</a>
                    <a class='list-group-item list-group-item-action' onclick=closeClusterForward(` +
            lastSelectedNode +
            `)>Cluster direct forward children</a>
                    </div>`;
        }
      }
      document.body.appendChild(menu);
    });
    document.addEventListener(
      'contextmenu',
      function (e) {
        e.preventDefault();
      },
      false,
    );

    // MIGHT CREATE BUGS IN OTHER FORMS vvvvvvv (disabling default submit event so the search bar of the graphs doesn't reload page on "Enter")
    document.addEventListener(
      'submit',
      function (e) {
        e.preventDefault();
      },
      false,
    );
  }
  // Remove context menu when clicking elsewhere
  network.on('click', function (params) {
    if (typeof ctxmenu !== 'undefined') {
      ctxmenu.outerHTML = '';
    }
  });
}

function printRecurseWarning(nodeLabel) {
  document.getElementById('hooker').innerHTML =
    `<div class="alert alert-dismissible alert-warning">
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    <h4 class="alert-heading">Warning!</h4>
    <p class="mb-0">The configuration of the graph doesn't allow to cluster ` +
    nodeLabel +
    ` </p>
    </div>`;
}

function createElementFromHTML(htmlString) {
  var div = document.createElement('a');
  div.innerHTML = htmlString.trim();
  return div.firstChild;
}

function hideSearchResults() {
  if (typeof searchbarResults !== 'undefined') {
    searchbarResults.outerHTML = '';
  }
}
