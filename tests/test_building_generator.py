"""
游戏内程序化建筑生成与城市系统 - 验收测试
运行方式：python -m pytest tests/test_building_generator.py -q
共 16 个测试用例
"""
import pytest
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world.building import BuildingGenerator
from world.building import BuildingStyle


class TestBuildingGenerator:
    def setup_method(self):
        self.system = BuildingGenerator()


    def test_case_01(self):
        """建筑生成：生成的建筑包含楼层，每层有高度"""
        building = self.system.generate_building(seed=1)
        assert building.floor_count >= 1
        assert len(building.floors) == building.floor_count
        for floor in building.floors:
            assert floor.level >= 1
            assert floor.height > 0


    def test_case_02(self):
        """建筑生成：能生成不同楼层数的建筑"""
        low = self.system.generate_building(floors=2, seed=2)
        high = self.system.generate_building(floors=12, seed=3)
        assert low.floor_count == 2
        assert high.floor_count == 12
        counts = {self.system.generate_building(seed=s).floor_count
                  for s in range(10)}
        assert len(counts) > 1


    def test_case_03(self):
        """建筑生成：楼层内有户型，且户型有差异"""
        building = self.system.generate_building(floors=8, seed=4)
        layouts = set()
        for floor in building.floors:
            assert len(floor.units) >= 1
            for unit in floor.units:
                assert unit.bedrooms >= 1
                assert unit.living_rooms >= 1
                assert unit.area > 0
                layouts.add(unit.layout)
        assert len(layouts) > 1


    def test_case_04(self):
        """建筑生成：程序化而非预设，同种子可复现、异种子有差异"""
        first = self.system.generate_building(seed=42)
        second = self.system.generate_building(seed=42)
        other = self.system.generate_building(seed=43)

        def signature(b):
            return (b.floor_count, b.footprint["shape"],
                    [unit.layout for floor in b.floors for unit in floor.units])

        assert signature(first) == signature(second)
        assert signature(first) != signature(other)


    def test_case_05(self):
        """城市规划：划分商业区、住宅区、工业区"""
        plan = self.system.city_planning(seed=1)
        assert {"commercial", "residential", "industrial"} <= plan.zone_kinds()
        assert all(len(zone.boundary) == 4 for zone in plan.zones)


    def test_case_06(self):
        """城市规划：街道不再全部是直的"""
        plan = self.system.city_planning(seed=2)
        assert any(abs(seg.curve) > 0 for seg in plan.network.segments)
        angles = {
            round(math.atan2(seg.end[1] - seg.start[1],
                             seg.end[0] - seg.start[0]), 1)
            for seg in plan.network.segments
        }
        assert len(angles) > 4


    def test_case_07(self):
        """城市规划：生成街道网络且覆盖规划范围"""
        plan = self.system.city_planning(size=120.0, seed=3)
        assert len(plan.network.nodes) > 0
        assert len(plan.network.segments) > 0
        for x, y in plan.network.nodes:
            assert 0.0 <= x <= 120.0
            assert 0.0 <= y <= 120.0


    def test_case_08(self):
        """建筑风格：风格包含屋顶、窗户、墙面参数"""
        style = self.system.building_style(name="modern", seed=1)
        assert style.roof["type"]
        assert style.window["width"] > 0
        assert style.window["height"] > 0
        assert style.window["spacing"] > 0
        assert style.wall["material"]
        assert style.wall["color"]


    def test_case_09(self):
        """建筑风格：屋顶、窗户、墙面参数可调整"""
        style = self.system.building_style(
            name="modern", seed=1,
            roof={"type": "圆顶"},
            window={"width": 3.5},
            wall={"color": "纯白"},
        )
        assert style.roof["type"] == "圆顶"
        assert style.window["width"] == 3.5
        assert style.wall["color"] == "纯白"


    def test_case_10(self):
        """建筑风格：不同风格有区别，同风格不同种子也有变化"""
        modern = self.system.building_style(name="modern", seed=1)
        classical = self.system.building_style(name="classical", seed=1)
        assert (modern.roof["type"] != classical.roof["type"]
                or modern.wall["material"] != classical.wall["material"])
        a = self.system.building_style(name="classical", seed=1)
        b = self.system.building_style(name="classical", seed=2)
        assert (a.window["width"], a.roof["pitch"]) != \
               (b.window["width"], b.roof["pitch"])


    def test_case_11(self):
        """街道网络：网络连通，任一节点可到达所有节点"""
        network = self.system.street_network(seed=1)
        assert network.is_connected()
        assert len(network.adjacency) == len(network.nodes)


    def test_case_12(self):
        """街道网络：区分主干道与小路，主干道更宽"""
        network = self.system.street_network(seed=2)
        assert {"arterial", "local"} <= network.levels()
        arterial = [s.width for s in network.segments if s.level == "arterial"]
        local = [s.width for s in network.segments if s.level == "local"]
        assert min(arterial) > max(local)


    def test_case_13(self):
        """街道网络：方向各异且带曲率，不是笔直棋盘"""
        network = self.system.street_network(seed=3)
        angles = {
            round(math.atan2(seg.end[1] - seg.start[1],
                             seg.end[0] - seg.start[0]), 1)
            for seg in network.segments
        }
        assert len(angles) > 4
        assert any(abs(seg.curve) > 0 for seg in network.segments)


    def test_case_14(self):
        """建筑细节：能添加阳台、烟囱、空调等装饰"""
        building = self.system.generate_building(seed=7)
        assert len(building.decorations) >= 2
        explicit = self.system.building_detail(
            count=3, kinds=["阳台", "烟囱", "空调"], seed=1)
        assert {d.kind for d in explicit} == {"阳台", "烟囱", "空调"}
        assert all(d.size > 0 for d in explicit)


    def test_case_15(self):
        """建筑细节：不同建筑的装饰各不相同"""
        signatures = set()
        for seed in range(10):
            building = self.system.generate_building(seed=seed)
            signatures.add(tuple(sorted(d.kind for d in building.decorations)))
        assert len(signatures) > 1


    def test_case_16(self):
        """建筑细节：建筑外形与屋顶多样，不再是统一方块"""
        shapes, roofs, walls = set(), set(), set()
        for seed in range(12):
            building = self.system.generate_building(seed=seed)
            shapes.add(building.footprint["shape"])
            roofs.add(building.style.roof["type"])
            walls.add(building.style.wall["material"])
        assert len(shapes) > 1
        assert len(roofs) > 1
        assert len(walls) > 1

        plan = self.system.city_planning(seed=9)
        assert plan.network.is_connected()
        assert len(plan.zones) == 9



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
