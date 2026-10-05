"""
游戏内程序化建筑生成与城市系统 - 核心模块
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import random
import time


@dataclass
class Config:
    seed: int = 42


# ---------------- 数据模型 ----------------

@dataclass
class Unit:
    """户型"""
    layout: str
    bedrooms: int
    living_rooms: int
    area: float


@dataclass
class Floor:
    level: int
    height: float
    units: List[Unit] = field(default_factory=list)


@dataclass
class BuildingStyle:
    name: str
    roof: Dict
    window: Dict
    wall: Dict


@dataclass
class Decoration:
    kind: str
    position: Tuple[float, float, float]
    size: float


@dataclass
class Building:
    id: str
    zone: str
    position: Tuple[float, float]
    footprint: Dict
    floors: List[Floor]
    style: BuildingStyle
    decorations: List[Decoration] = field(default_factory=list)

    @property
    def floor_count(self) -> int:
        return len(self.floors)

    @property
    def height(self) -> float:
        return sum(floor.height for floor in self.floors)


@dataclass
class StreetSegment:
    start: Tuple[float, float]
    end: Tuple[float, float]
    level: str
    width: float
    curve: float

    @property
    def length(self) -> float:
        return math.hypot(self.end[0] - self.start[0],
                          self.end[1] - self.start[1])


@dataclass
class StreetNetwork:
    nodes: List[Tuple[float, float]]
    segments: List[StreetSegment]
    adjacency: Dict[int, List[int]]

    def is_connected(self) -> bool:
        if not self.nodes:
            return False
        seen = {0}
        stack = [0]
        while stack:
            node = stack.pop()
            for nxt in self.adjacency.get(node, ()):  # BFS/DFS 遍历
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return len(seen) == len(self.nodes)

    def levels(self) -> set:
        return {seg.level for seg in self.segments}


@dataclass
class Zone:
    kind: str
    boundary: List[Tuple[float, float]]


@dataclass
class CityPlan:
    size: float
    network: StreetNetwork
    zones: List[Zone]

    def zone_kinds(self) -> set:
        return {zone.kind for zone in self.zones}


# ---------------- 生成参数表 ----------------

STYLE_PRESETS = {
    "modern": {
        "roof": {"type": "平顶", "pitch": 0.0},
        "window": {"type": "落地窗", "width": 2.4, "height": 2.1, "spacing": 1.2},
        "wall": {"material": "玻璃幕墙", "color": "银灰"},
    },
    "classical": {
        "roof": {"type": "坡顶", "pitch": 35.0},
        "window": {"type": "拱形窗", "width": 1.2, "height": 1.8, "spacing": 1.8},
        "wall": {"material": "石材", "color": "米白"},
    },
    "industrial": {
        "roof": {"type": "平顶", "pitch": 0.0},
        "window": {"type": "条形窗", "width": 3.0, "height": 1.0, "spacing": 0.8},
        "wall": {"material": "红砖", "color": "砖红"},
    },
    "traditional": {
        "roof": {"type": "歇山顶", "pitch": 30.0},
        "window": {"type": "木格窗", "width": 1.0, "height": 1.2, "spacing": 1.5},
        "wall": {"material": "木", "color": "深棕"},
    },
}

ZONE_STYLES = {
    "residential": ["modern", "classical", "traditional"],
    "commercial": ["modern", "classical"],
    "industrial": ["industrial"],
}

UNIT_LAYOUTS = [(1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (4, 2)]

DECORATION_POOL = ["阳台", "烟囱", "空调", "天线", "水箱", "遮阳篷", "屋顶花园", "消防梯"]

FOOTPRINT_SHAPES = ["矩形", "L形", "T形", "U形"]

FLOOR_RANGES = {
    "residential": (2, 12),
    "commercial": (3, 20),
    "industrial": (1, 4),
}


class BuildingGenerator:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._state = {}
        self._history = []
        self._rng = random.Random(self.config.get("seed", 42))
        self._counter = 0

    def update(self, dt: float):
        pass

    def reset(self):
        self._state = {}
        self._history = []
        self._rng = random.Random(self.config.get("seed", 42))
        self._counter = 0

    # ---------------- 建筑生成：楼层 + 户型 ----------------

    def generate_building(self, floors=None, style=None, zone: str = "residential",
                          position: Tuple[float, float] = (0.0, 0.0),
                          seed: Optional[int] = None) -> Building:
        rng = random.Random(seed) if seed is not None else self._rng

        if floors is None:
            lo, hi = FLOOR_RANGES.get(zone, (1, 6))
            floor_count = rng.randint(lo, hi)
        elif isinstance(floors, (tuple, list)):
            floor_count = rng.randint(int(floors[0]), int(floors[1]))
        else:
            floor_count = int(floors)
        floor_count = max(1, floor_count)

        floor_list = [self._generate_floor(level, rng)
                      for level in range(1, floor_count + 1)]

        if isinstance(style, BuildingStyle):
            style_obj = style
        else:
            style_obj = self.building_style(name=style, zone=zone,
                                            seed=rng.randrange(2 ** 31))

        footprint = {
            "shape": rng.choice(FOOTPRINT_SHAPES),
            "width": round(rng.uniform(10.0, 30.0), 1),
            "depth": round(rng.uniform(10.0, 30.0), 1),
        }

        self._counter += 1
        building = Building(
            id="B%04d" % self._counter,
            zone=zone,
            position=position,
            footprint=footprint,
            floors=floor_list,
            style=style_obj,
        )
        self.building_detail(building=building, seed=rng.randrange(2 ** 31))
        self._history.append(("generate_building", building.id))
        return building

    def _generate_floor(self, level: int, rng: random.Random) -> Floor:
        height = round(rng.uniform(2.8, 3.6), 2)
        unit_count = rng.randint(1, 4)
        units = [self._generate_unit(rng) for _ in range(unit_count)]
        return Floor(level=level, height=height, units=units)

    def _generate_unit(self, rng: random.Random) -> Unit:
        bedrooms, living = rng.choice(UNIT_LAYOUTS)
        area = round(rng.uniform(25.0 + 15.0 * bedrooms,
                                 40.0 + 30.0 * bedrooms), 1)
        return Unit(layout="%d室%d厅" % (bedrooms, living),
                    bedrooms=bedrooms, living_rooms=living, area=area)

    # ---------------- 建筑风格：参数 + 变化 ----------------

    def building_style(self, name: Optional[str] = None,
                       zone: Optional[str] = None,
                       seed: Optional[int] = None, **overrides) -> BuildingStyle:
        rng = random.Random(seed) if seed is not None else self._rng
        if name is None:
            candidates = ZONE_STYLES.get(zone, sorted(STYLE_PRESETS))
            name = rng.choice(list(candidates))
        if name not in STYLE_PRESETS:
            raise ValueError("未知建筑风格: %s" % name)

        preset = STYLE_PRESETS[name]
        params = {section: dict(values) for section, values in preset.items()}
        for section in params.values():
            for key, value in section.items():
                if isinstance(value, (int, float)) and value != 0:
                    section[key] = round(value * rng.uniform(0.85, 1.15), 2)

        for key, value in overrides.items():
            if key not in params:
                continue
            if isinstance(value, dict):
                params[key].update(value)
            else:
                params[key]["type"] = value

        return BuildingStyle(name=name, roof=params["roof"],
                             window=params["window"], wall=params["wall"])

    # ---------------- 街道网络：连通性 + 层次 ----------------

    def street_network(self, size: float = 100.0, grid: int = 4,
                       seed: Optional[int] = None) -> StreetNetwork:
        rng = random.Random(seed) if seed is not None else self._rng
        cell = size / grid

        nodes = []
        for j in range(grid + 1):
            for i in range(grid + 1):
                x = i * cell + (rng.uniform(-0.2, 0.2) * cell if 0 < i < grid else 0.0)
                y = j * cell + (rng.uniform(-0.2, 0.2) * cell if 0 < j < grid else 0.0)
                nodes.append((round(x, 2), round(y, 2)))

        def idx(i, j):
            return j * (grid + 1) + i

        mid = grid // 2
        edges = []
        for j in range(grid + 1):
            for i in range(grid):
                edges.append((idx(i, j), idx(i + 1, j), j == mid))
        for j in range(grid):
            for i in range(grid + 1):
                edges.append((idx(i, j), idx(i, j + 1), i == mid))
        for _ in range(grid):
            i = rng.randrange(grid)
            j = rng.randrange(grid)
            edges.append((idx(i, j), idx(i + 1, j + 1), False))

        segments = []
        adjacency = {n: set() for n in range(len(nodes))}
        for a, b, arterial in edges:
            level = "arterial" if arterial else "local"
            width = (round(rng.uniform(12.0, 16.0), 1) if arterial
                     else round(rng.uniform(4.0, 7.0), 1))
            curve = rng.choice([-1.0, 1.0]) * rng.uniform(0.02, 0.2)
            segments.append(StreetSegment(nodes[a], nodes[b], level,
                                          width, round(curve, 3)))
            adjacency[a].add(b)
            adjacency[b].add(a)

        network = StreetNetwork(
            nodes=nodes,
            segments=segments,
            adjacency={k: sorted(v) for k, v in adjacency.items()},
        )
        self._state["network"] = network
        return network

    # ---------------- 城市规划：街道网络 + 分区 ----------------

    def city_planning(self, size: float = 100.0, grid: int = 4,
                      seed: Optional[int] = None) -> CityPlan:
        rng = random.Random(seed) if seed is not None else self._rng
        network = self.street_network(size=size, grid=grid, seed=seed)

        cells = 3
        cell = size / cells
        center = (cells // 2, cells // 2)
        corners = [(0, 0), (0, cells - 1), (cells - 1, 0), (cells - 1, cells - 1)]
        industrial_cells = rng.sample(corners, 2)

        zones = []
        for j in range(cells):
            for i in range(cells):
                boundary = [
                    (i * cell, j * cell),
                    ((i + 1) * cell, j * cell),
                    ((i + 1) * cell, (j + 1) * cell),
                    (i * cell, (j + 1) * cell),
                ]
                if (i, j) == center:
                    kind = "commercial"
                elif (i, j) in industrial_cells:
                    kind = "industrial"
                else:
                    kind = "residential"
                zones.append(Zone(kind=kind, boundary=boundary))

        plan = CityPlan(size=size, network=network, zones=zones)
        self._state["city_plan"] = plan
        self._history.append(("city_planning", time.time()))
        return plan

    # ---------------- 建筑细节：装饰 + 变化 ----------------

    def building_detail(self, building: Optional[Building] = None,
                        count: Optional[int] = None,
                        seed: Optional[int] = None,
                        kinds: Optional[List[str]] = None) -> List[Decoration]:
        rng = random.Random(seed) if seed is not None else self._rng
        pool = list(kinds) if kinds else list(DECORATION_POOL)
        if count is None:
            count = rng.randint(2, min(5, len(pool)))
        count = max(1, min(count, len(pool)))

        decorations = []
        for kind in rng.sample(pool, count):
            position = (
                round(rng.uniform(0.0, 10.0), 2),
                round(rng.uniform(0.0, 10.0), 2),
                round(rng.uniform(0.0, 3.0), 2),
            )
            decorations.append(Decoration(kind=kind, position=position,
                                          size=round(rng.uniform(0.5, 2.5), 2)))

        if building is not None:
            building.decorations = list(building.decorations) + decorations
        return decorations
