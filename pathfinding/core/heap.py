"""Simple heap with ordering and removal."""
import heapq
from .graph import Graph
from .grid import Grid
from .world import World


class SimpleHeap:
    """Simple wrapper around open_list that keeps track of order and removed
    nodes automatically."""

    def __init__(self, node, grid):
        self.grid = grid
        self.open_list = [self._get_node_tuple(node, 0)]
        self.number_pushed = 0

    def _get_node_tuple(self, node, heap_order):
        if isinstance(self.grid, Graph):
            return (node.f, heap_order, node.node_id)
        elif isinstance(self.grid, Grid):
            return (node.f, heap_order, node.x, node.y)
        elif isinstance(self.grid, World):
            return (node.f, heap_order, node.x, node.y, node.grid_id)
        else:
            assert False, "unsupported heap node node=%s" % node

    def pop_node(self):
        """
        Pops node off the heap. i.e. returns the one with the lowest f.

        Notes:
        1. Checks if that values is in removed_node_tuples first, if not tries
           again.
        2. We use this approach to avoid invalidating the heap structure.
        """
        # EVOLVE-BLOCK-START id="heap-optimization"
        while self.open_list:
            node_tuple = heapq.heappop(self.open_list)

            if isinstance(self.grid, Graph):
                node = self.grid.node(node_tuple[2])
            elif isinstance(self.grid, Grid):
                node = self.grid.node(node_tuple[2], node_tuple[3])
            elif isinstance(self.grid, World):
                node = self.grid.grids[
                    node_tuple[4]].node(node_tuple[2], node_tuple[3])

            if not node.closed:
                return node
        return None
        # EVOLVE-BLOCK-END

    def push_node(self, node):
        """
        Push node into heap.

        :param node: The node to push.
        """
        # EVOLVE-BLOCK-START id="heap-optimization"
        self.number_pushed = self.number_pushed + 1
        node_tuple = self._get_node_tuple(node, self.number_pushed)
        heapq.heappush(self.open_list, node_tuple)
        # EVOLVE-BLOCK-END

    def remove_node(self, node, f):
        """
        Remove the node from the heap.

        This just stores it in a set and we just ignore the node if it does
        get popped from the heap.

        :param node: The node to remove.
        :param f: The old f value of the node.
        """
        # EVOLVE-BLOCK-START id="heap-optimization"
        # This method is no longer used due to simplification.
        pass
        # EVOLVE-BLOCK-END

    def __len__(self):
        """Returns the length of the open_list."""
        return len(self.open_list)