from datetime import datetime
from typing import Any


class PipelineNode:
    def __init__(self, name: str, data: dict[str, Any] | None = None) -> None:
        """Initializes a Node with a name and data."""
        self.name = name
        self.data = data
        self.parents: list[str] = []
        self.children: list[str] = []

    def is_root(self) -> bool:
        return len(self.parents) == 0

    def is_leaf(self) -> bool:
        return len(self.children) == 0


class PipelineEdge:
    def __init__(self, start: str, end: str, data: dict[str, Any]):
        """Initializes a connection between two nodes in a pipeline."""
        self.start = start
        self.end = end
        self.data = data


class PipelineResult:
    """Container for pipeline execution results."""

    def __init__(self, run_id: str, results: dict[str, Any]):
        """Initializes a result with id."""
        self.run_id = run_id
        self.results = results
        self.timestamp = datetime.now()


class PipelineGraph[GenericNode: PipelineNode, GenericEdge: PipelineEdge]:
    """
    When defining a pipeline, user must define their node and edge types.

    Node type must inherit from PipelineNode
    Edge type must inherit from PipelineEdge
    """

    def __init__(self) -> None:
        """Initializes a Pipeline with a set of nodes and edges."""
        self._nodes: dict[str, GenericNode] = {}
        self._edges: list[GenericEdge] = []

    def add_node(self, node: GenericNode) -> None:
        if node in self:
            raise ValueError(
                f"Node {node.name} already exists, use 'set_node' if you want to replace it."
            )
        self._nodes[node.name] = node

    def set_node(self, node: GenericNode) -> None:
        """Replace an existing node with a new one based on node name."""
        if node not in self:
            raise ValueError(
                f"Node {node.name} does not exist, use `add_node` instead."
            )
        # propagate the graph info to the new node:
        old_node = self._nodes[node.name]
        node.parents = old_node.parents
        node.children = old_node.children
        self._nodes[node.name] = node

    def _validate_edge(self, start: str, end: str) -> None:
        if start not in self:
            raise KeyError(f"Node {start} does not exist")
        if end not in self:
            raise KeyError(f"Node {end} does not exist")
        for edge in self._edges:
            if edge.start == start and edge.end == end:
                raise ValueError(f"{start} and {end} are already connected")

    def add_edge(self, edge: GenericEdge) -> None:
        self._validate_edge(edge.start, edge.end)
        self._edges.append(edge)
        self._nodes[edge.end].parents.append(edge.start)
        self._nodes[edge.start].children.append(edge.end)

    def get_node_by_name(self, name: str) -> GenericNode:
        node = self._nodes[name]
        return node

    def roots(self) -> list[GenericNode]:
        root = []
        for node in self._nodes.values():
            if node.is_root():
                root.append(node)
        return root

    def leaves(self) -> list[GenericNode]:
        """Get all leaf nodes (nodes with no children)."""
        return [node for node in self._nodes.values() if node.is_leaf()]

    def next_edges(self, node: str) -> list[GenericEdge]:
        res = []
        for edge in self._edges:
            if edge.start == node:
                res.append(edge)
        return res

    def previous_edges(self, node: str) -> list[GenericEdge]:
        res = []
        for edge in self._edges:
            if edge.end == node:
                res.append(edge)
        return res

    def __contains__(self, node: GenericNode | str) -> bool:
        """Check if a node is in a pipeline."""
        if isinstance(node, str):
            return node in self._nodes
        return node.name in self._nodes

    def dfs(self, visited: set[str], node: str) -> bool:
        if node in visited:
            return True
        else:
            for edge in self.next_edges(node):
                if self.dfs(visited | {node}, edge.end):
                    return True
            return False

    def is_cyclic(self) -> bool:
        """Returns True if at least one cycle found in graph.

        Traverse the graph from each node.
        If the same node is encountered again,
        the graph is cyclic.
        """
        for node in self._nodes:
            if self.dfs(set(), node):
                return True
        return False
