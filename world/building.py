"""
游戏内程序化建筑生成与城市系统 - 核心模块

提供：
- generate_building(): 程序化建筑生成（楼层 + 户型）
- city_planning():     城市规划（街道网络 + 功能分区）
- building_style():    建筑风格（参数化 + 变化）
- street_network():    街道网络（连通性 + 层次）
- building_detail():   建筑细节（装饰 + 变化）
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math
import random
import time


@dataclass
class Config:
    pass


# 户型库：不同建筑类型对应不同户型
LAYOUTS: Dict[str, List[str]] = {
    "residential": ["studio", "one_bedroom", "two_bedroom", "three_bedroom", "penthouse"],
    "commercial": ["retail", "office", "restaurant", "hotel_suite"],
    "industrial": ["warehouse", "workshop", "factory_floor"],
}

# 风格预设：屋顶 / 窗户 / 墙面均可参数化
STYLE_PRESETS: Dict[str, Dict] = {
    "modern": {"roof": "flat", "window_style": "ribbon", "window_ratio": 0.60, "wall_material": "glass"},
    "classical": {"roof": "mansard", "window_style": "arched", "window_ratio": 0.30, "wall_material": "stone"},
    "traditional": {"roof": "gable", "window_style": "casement", "window_ratio": 0.25, "wall_material": "brick"},
    "industrial": {"roof": "sawtooth", "window_style": "grid", "window_ratio": 0.20, "wall_material": "concrete"},
}

ROOF_TYPES = ["flat", "gable", "hip", "mansard", "dome", "sawtooth"]
WALL_MATERIALS = ["glass", "stone", "brick", "concrete", "wood", "metal"]
WALL_COLORS = ["white", "beige", "gray", "red", "brown", "blue", "green", "yellow"]

# 装饰库：阳台、烟囱、空调等
DECORATION_TYPES = ["balcony", "chimney", "ac_unit", "awning", "roof_garden", "antenna", "dormer", "fire_escape"]

# 街道层次：主干道 / 次干道 / 小路
STREET_LEVELS = ["arterial", "collector", "local"]

ZONE_TYPES = ["commercial", "residential", "industrial"]


class BuildingGenerator:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._state = {}
        self._history = []
        self._counter = 0

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._state["last_update"] = time.time()

    def reset(self):
        self._state = {}
        self._history = []
        self._counter = 0

    # ------------------------------------------------------------------
    # 建筑生成：楼层 + 户型
    # ------------------------------------------------------------------
    def generate_building(
        self,
        floors: Optional[int] = None,
        layout: Optional[str] = None,
        style: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict:
        """程序化生成一栋建筑。

        - floors: 楼层数（缺省随机 2~30）
        - layout: 户型类别（residential/commercial/industrial，缺省随机）
        - style:  建筑风格（缺省随机）
        返回包含逐楼层户型、风格与细节的建筑描述。
        """
        rng = random.Random(seed)
        floor_count = floors if floors is not None else rng.randint(2, 30)
        if floor_count < 1:
            raise ValueError("floors must be >= 1")
        layout = layout or rng.choice(list(LAYOUTS))
        if layout not in LAYOUTS:
            raise ValueError(f"unknown layout: {layout}")

        unit_types = LAYOUTS[layout]
        floor_list = []
        for level in range(1, floor_count + 1):
            units_per_floor = rng.randint(1, 4)
            units = [
                {
                    "type": rng.choice(unit_types),
                    "area": round(rng.uniform(30.0, 200.0), 1),
                    "rooms": rng.randint(1, 5),
                }
                for _ in range(units_per_floor)
            ]
            floor_list.append({"level": level, "units": units})

        self._counter += 1
        building = {
            "id": self._counter,
            "floor_count": floor_count,
            "floors": floor_list,
            "layout": layout,
            "style": self.building_style(style, rng=rng),
            "height": round(floor_count * rng.uniform(2.8, 3.5), 2),
            "footprint": (round(rng.uniform(8, 30), 1), round(rng.uniform(8, 30), 1)),
        }
        building["details"] = self.building_detail(building, rng=rng)
        self._history.append(building)
        return building

    # ------------------------------------------------------------------
    # 建筑风格：参数化 + 变化
    # ------------------------------------------------------------------
    def building_style(self, style: Optional[str] = None, rng: Optional[random.Random] = None, **overrides) -> Dict:
        """生成风格参数。屋顶、窗户、墙面均可通过 overrides 调整，
        并在预设基础上加入随机扰动，保证每栋建筑的风格都有差异。"""
        rng = rng or random.Random()
        name = style or rng.choice(list(STYLE_PRESETS))
        if name not in STYLE_PRESETS:
            raise ValueError(f"unknown style: {name}")
        params = dict(STYLE_PRESETS[name])
        params.update({k: v for k, v in overrides.items() if v is not None})
        # 风格变化：参数扰动
        params["window_ratio"] = round(
            min(0.95, max(0.05, params["window_ratio"] + rng.uniform(-0.08, 0.08))), 2
        )
        params["wall_color"] = rng.choice(WALL_COLORS)
        params["name"] = name
        return params

    # ------------------------------------------------------------------
    # 街道网络：连通性 + 层次 + 有机形态
    # ------------------------------------------------------------------
    def street_network(
        self,
        num_intersections: int = 12,
        bounds: Tuple[float, float] = (200.0, 200.0),
        seed: Optional[int] = None,
    ) -> Dict:
        """生成有机街道网络。

        - 连通性：以 Prim 最小生成树为骨架，保证全图连通，再补充环路
        - 层次：主干道(arterial) / 次干道(collector) / 小路(local)
        - 有机形态：每条街道为带中间偏移点的折线，而非直线
        """
        rng = random.Random(seed)
        width, height = bounds
        n = max(2, num_intersections)

        nodes = []
        for i in range(n):
            nodes.append(
                {
                    "id": i,
                    "pos": (round(rng.uniform(0, width), 2), round(rng.uniform(0, height), 2)),
                }
            )

        def dist(a, b):
            ax, ay = nodes[a]["pos"]
            bx, by = nodes[b]["pos"]
            return math.hypot(ax - bx, ay - by)

        # Prim 最小生成树 -> 保证连通
        in_tree = {0}
        mst_edges = []
        while len(in_tree) < n:
            best = None
            for u in in_tree:
                for v in range(n):
                    if v in in_tree:
                        continue
                    d = dist(u, v)
                    if best is None or d < best[2]:
                        best = (u, v, d)
            u, v, _ = best
            in_tree.add(v)
            mst_edges.append((u, v))

        # 补充环路，让网络更自然
        extra = []
        existing = {tuple(sorted(e)) for e in mst_edges}
        candidates = [
            (i, j) for i in range(n) for j in range(i + 1, n) if (i, j) not in existing
        ]
        rng.shuffle(candidates)
        for u, v in candidates[: max(1, n // 3)]:
            extra.append((u, v))

        all_pairs = mst_edges + extra
        lengths = [dist(u, v) for u, v in all_pairs]
        sorted_lengths = sorted(lengths, reverse=True)
        arterial_cut = sorted_lengths[max(0, len(sorted_lengths) // 4 - 1)]
        collector_cut = sorted_lengths[max(0, len(sorted_lengths) // 2 - 1)]

        edges = []
        for idx, ((u, v), length) in enumerate(zip(all_pairs, lengths)):
            if length >= arterial_cut:
                level = "arterial"
            elif length >= collector_cut:
                level = "collector"
            else:
                level = "local"
            edges.append(
                {
                    "id": idx,
                    "from": u,
                    "to": v,
                    "level": level,
                    "length": round(length, 2),
                    "path": self._organic_path(nodes[u]["pos"], nodes[v]["pos"], rng),
                }
            )

        network = {"nodes": nodes, "edges": edges}
        network["connected"] = self._is_connected(network)
        return network

    @staticmethod
    def _organic_path(p0, p1, rng, segments: int = 3) -> List[Tuple[float, float]]:
        """在两端点之间生成带随机垂直偏移的折线，使街道不是直线。"""
        x0, y0 = p0
        x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length  # 法向
        path = [(round(x0, 2), round(y0, 2))]
        for i in range(1, segments):
            t = i / segments
            offset = rng.uniform(-0.15, 0.15) * length
            path.append((round(x0 + dx * t + nx * offset, 2), round(y0 + dy * t + ny * offset, 2)))
        path.append((round(x1, 2), round(y1, 2)))
        return path

    @staticmethod
    def _is_connected(network: Dict) -> bool:
        nodes = network["nodes"]
        if not nodes:
            return True
        adj = {node["id"]: [] for node in nodes}
        for edge in network["edges"]:
            adj[edge["from"]].append(edge["to"])
            adj[edge["to"]].append(edge["from"])
        seen = {nodes[0]["id"]}
        stack = [nodes[0]["id"]]
        while stack:
            cur = stack.pop()
            for nxt in adj[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return len(seen) == len(nodes)

    # ------------------------------------------------------------------
    # 城市规划：街道网络 + 功能分区
    # ------------------------------------------------------------------
    def city_planning(
        self,
        width: float = 300.0,
        height: float = 300.0,
        seed: Optional[int] = None,
        grid: Tuple[int, int] = (3, 3),
        buildings_per_zone: int = 3,
    ) -> Dict:
        """生成城市规划：功能分区（商业/住宅/工业）+ 有机街道网络 + 建筑布局。"""
        rng = random.Random(seed)
        cols, rows = grid

        # 分区：保证三种功能区都出现
        zone_pool = ZONE_TYPES.copy()
        zones = []
        for r in range(rows):
            for c in range(cols):
                if zone_pool:
                    ztype = zone_pool.pop(rng.randrange(len(zone_pool)))
                else:
                    ztype = rng.choice(ZONE_TYPES)
                zones.append(
                    {
                        "type": ztype,
                        "bounds": (
                            round(c * width / cols, 2),
                            round(r * height / rows, 2),
                            round((c + 1) * width / cols, 2),
                            round((r + 1) * height / rows, 2),
                        ),
                    }
                )
        rng.shuffle(zones)

        network = self.street_network(
            num_intersections=max(6, cols * rows),
            bounds=(width, height),
            seed=rng.randrange(2**31),
        )

        # 每个分区内按功能生成建筑
        buildings = []
        for zone in zones:
            x0, y0, x1, y1 = zone["bounds"]
            for _ in range(buildings_per_zone):
                b = self.generate_building(
                    layout=zone["type"],
                    seed=rng.randrange(2**31),
                )
                b["position"] = (
                    round(rng.uniform(x0, x1), 2),
                    round(rng.uniform(y0, y1), 2),
                )
                b["zone"] = zone["type"]
                buildings.append(b)

        return {
            "size": (width, height),
            "zones": zones,
            "street_network": network,
            "buildings": buildings,
        }

    # ------------------------------------------------------------------
    # 建筑细节：装饰 + 变化
    # ------------------------------------------------------------------
    def building_detail(
        self,
        building: Optional[Dict] = None,
        rng: Optional[random.Random] = None,
        seed: Optional[int] = None,
    ) -> Dict:
        """为建筑生成细节：随机装饰（阳台/烟囱/空调等）与立面分段，
        保证每栋建筑的细节都不一样，不再是纯方块。"""
        rng = rng or random.Random(seed)
        floor_count = building["floor_count"] if building else rng.randint(2, 20)

        decorations = []
        for deco in DECORATION_TYPES:
            if rng.random() < 0.55:
                decorations.append(
                    {
                        "type": deco,
                        "count": rng.randint(1, max(2, floor_count)),
                        "floors": sorted(rng.sample(range(1, floor_count + 1), k=min(floor_count, rng.randint(1, 3)))),
                    }
                )

        facade = [
            {"segment": i, "material": rng.choice(WALL_MATERIALS), "color": rng.choice(WALL_COLORS)}
            for i in range(rng.randint(2, 5))
        ]

        return {
            "decorations": decorations,
            "facade": facade,
            "corner_radius": round(rng.uniform(0.0, 2.0), 2),
            "setback_floors": sorted(rng.sample(range(2, floor_count + 1), k=min(floor_count - 1, rng.randint(0, 2)))) if floor_count > 1 else [],
        }
