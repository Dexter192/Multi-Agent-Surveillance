from typing import Tuple, List
import math
import numpy as np
import vectormath as vmath

from . import pathfinding


class MapView(pathfinding.Graph):
    """
    Basically implements a fog-of-war
    """

    def __init__(self, map):
        # private copy of the full map
        self._map = map

        # fog-of-war map
        self.fog = np.zeros((self._map.size[0], self._map.size[1]), dtype=np.bool)

    def _reveal_all(self):
        self.fog = np.ones((self._map.size[0], self._map.size[1]), dtype=np.bool)

    def _reveal_circle(self, x: int, y: int, radius: float):
        # center = vmath.Vector2(x, y)
        # min_x = max(0, int(x - radius - 1))
        # max_x = min(self._map.size[0], int(x + radius + 1))
        # min_y = max(0, int(y - radius - 1))
        # max_y = min(self._map.size[1], int(y + radius + 1))
        # for x in range(min_x, max_x):
        #     for y in range(min_y, max_y):
        #         if (center - (x + 0.5, y + 0.5)).length < radius:
        #             self.fog[x][y] = True

        radius = int(math.ceil(radius))

        width = radius * 2 + 1
        z = np.zeros((width, width), dtype=np.bool)

        # calculate distance for each point in the matrix
        X, Y = np.meshgrid(np.arange(z.shape[0]), np.arange(z.shape[1]))
        dist = np.sqrt((X - width // 2)**2 + (Y - width // 2)**2)

        # assign value of 1 to those points where `dist < radius`
        z[np.where(dist <= radius)] = 1

        # `paste` and `paste_slices` taken from:
        # https://stackoverflow.com/a/50692782
        def paste(wall, block, loc):
            def paste_slices(tup):
                pos, w, max_w = tup
                wall_min = max(pos, 0)
                wall_max = min(pos + w, max_w)
                block_min = -min(pos, 0)
                block_max = max_w - max(pos + w, max_w)
                block_max = block_max if block_max != 0 else None
                return slice(wall_min, wall_max), slice(block_min, block_max)
            loc_zip = zip(loc, block.shape, wall.shape)
            wall_slices, block_slices = zip(*map(paste_slices, loc_zip))
            wall[wall_slices] += block[block_slices]

        paste(self.fog, z, (x - width // 2, y - width // 2))
        # print('vision updated')

        # offset_x = x - width // 2
        # offset_y = y - width // 2
        # self.fog[offset_x:width + offset_x, offset_y:width + offset_y] |= z

    def is_revealed(self, x: int, y: int):
        if x >= 0 and y >= 0 and x < self._map.size[0] and y < self._map.size[1]:
            return self.fog[x][y]
        else:
            return True

    # vvvv pathfinding methods vvvv

    def neighbors(self, node):
        """ Implements abstract method `neighbors` from `Graph` """
        (x, y) = node
        # NESW only
        # results = [(x + 1, y), (x, y - 1), (x - 1, y), (x, y + 1)]
        # with diagonals
        results = [(x + 1, y), (x + 1, y - 1), (x, y - 1), (x - 1, y - 1), (x - 1, y), (x - 1, y + 1), (x, y + 1), (x + 1, y + 1)]
        # if (x + y) % 2 == 0:
        #     results.reverse()  # aesthetics
        results = filter(lambda node: self._map.in_bounds(*node), results)
        results = filter(lambda node: not (self.is_revealed(*node) and self._map.is_wall(*node)), results)
        return results

    def cost(self, from_node, to_node):
        """ Implements abstract method `cost` from `Graph` """
        x1, y1 = from_node
        x2, y2 = to_node

        # diagonal
        if (x2 - x1 + y2 - y1) % 2 == 0:
            multiplier = 2**0.5
        # straight
        else:
            multiplier = 1

        # double cost for "invisible" tiles
        if self.is_revealed(*to_node):
            return 2 * multiplier
        else:
            return 1 * multiplier

    def find_path(self, from_node: Tuple[float, float], to_node: Tuple[float, float]) -> List[Tuple[float, float]]:
        def heuristic(from_node, to_node):
            (x0, y0) = from_node
            (x1, y1) = to_node
            D = 1  # NESW cost
            D2 = 2**0.5  # diagonal cost
            dx = abs(x0 - x1)
            dy = abs(y0 - y1)
            return D * (dx + dy) + (D2 - 2 * D) * min(dx, dy)

        # make start and goal positions into `int`s
        from_node = (int(from_node[0]), int(from_node[1]))
        to_node = (int(to_node[0]), int(to_node[1]))

        came_from, cost_so_far = pathfinding.a_star_search(self, from_node, to_node, heuristic)
        path = pathfinding.reconstruct_path(came_from, from_node, to_node)
        # map the path from tile coordinates to agent coordinates
        path = list(map(lambda node: vmath.Vector2(node[0] + 0.5, node[1] + 0.5), path))

        return path


    # vvvv copy methods from map.Map vvvv

    def is_wall(self, x: int, y: int) -> bool:
        return self._map.is_wall(x, y)
