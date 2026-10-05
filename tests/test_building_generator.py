"""
游戏内程序化建筑生成与城市系统 - 验收测试
运行方式：python -m pytest tests/test_building_generator.py -q
共 16 个测试用例
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world.building import BuildingGenerator


class TestBuildingGenerator:
    def setup_method(self):
        self.system = BuildingGenerator()

    # ---- generate_building: 楼层 ----
    def test_case_01(self):
        b = self.system.generate_building(floors=6, seed=1)
        assert b["floor_count"] == 6
        assert len(b["floors"]) == 6
        assert [f["level"] for f in b["floors"]] == [1, 2, 3, 4, 5, 6]

    def test_case_02(self):
        tall = self.system.generate_building(floors=25, seed=2)
        short = self.system.generate_building(floors=2, seed=3)
        assert tall["floor_count"] != short["floor_count"]
        assert tall["height"] > short["height"]

    # ---- generate_building: 户型 ----
    def test_case_03(self):
        b = self.system.generate_building(layout="residential", floors=3, seed=4)
        assert b["layout"] == "residential"
        for floor in b["floors"]:
            assert floor["units"], "每层必须有户型"
            for unit in floor["units"]:
                assert unit["type"] in ("studio", "one_bedroom", "two_bedroom", "three_bedroom", "penthouse")
                assert unit["area"] > 0 and unit["rooms"] >= 1

    def test_case_04(self):
        res = self.system.generate_building(layout="residential", floors=5, seed=5)
        com = self.system.generate_building(layout="commercial", floors=5, seed=5)
        res_units = {u["type"] for f in res["floors"] for u in f["units"]}
        com_units = {u["type"] for f in com["floors"] for u in f["units"]}
        assert res_units and com_units and res_units != com_units

    # ---- city_planning: 分区 ----
    def test_case_05(self):
        plan = self.system.city_planning(seed=10)
        zone_types = {z["type"] for z in plan["zones"]}
        assert {"commercial", "residential", "industrial"} <= zone_types

    # ---- city_planning: 街道网络 + 建筑落位 ----
    def test_case_06(self):
        plan = self.system.city_planning(seed=11)
        assert plan["street_network"]["edges"]
        assert plan["buildings"]
        for b in plan["buildings"]:
            assert b["layout"] == b["zone"]
            x, y = b["position"]
            assert 0 <= x <= plan["size"][0] and 0 <= y <= plan["size"][1]

    def test_case_07(self):
        plan = self.system.city_planning(seed=12)
        assert plan["street_network"]["connected"] is True

    # ---- building_style: 参数可调 ----
    def test_case_08(self):
        import random
        style = self.system.building_style("modern", roof="dome", window_ratio=0.9,
                                           rng=random.Random(0))
        assert style["roof"] == "dome"
        assert abs(style["window_ratio"] - 0.9) <= 0.08
        assert style["wall_material"] in ("glass", "stone", "brick", "concrete", "wood", "metal")

    # ---- building_style: 风格有变化 ----
    def test_case_09(self):
        modern = self.system.building_style("modern", rng=__import__("random").Random(1))
        classical = self.system.building_style("classical", rng=__import__("random").Random(1))
        assert (modern["roof"], modern["window_style"], modern["wall_material"]) != \
               (classical["roof"], classical["window_style"], classical["wall_material"])

    def test_case_10(self):
        import random
        signatures = {
            self.system.building_style("modern", rng=random.Random(i))["window_ratio"]
            for i in range(40)
        }
        assert len(signatures) > 1, "同一风格也必须有参数变化"

    # ---- street_network: 连通性 ----
    def test_case_11(self):
        net = self.system.street_network(num_intersections=15, seed=20)
        assert net["connected"] is True
        reached = {net["nodes"][0]["id"]}
        stack = [net["nodes"][0]["id"]]
        adj = {n["id"]: [] for n in net["nodes"]}
        for e in net["edges"]:
            adj[e["from"]].append(e["to"])
            adj[e["to"]].append(e["from"])
        while stack:
            cur = stack.pop()
            for nxt in adj[cur]:
                if nxt not in reached:
                    reached.add(nxt)
                    stack.append(nxt)
        assert reached == {n["id"] for n in net["nodes"]}

    # ---- street_network: 层次 ----
    def test_case_12(self):
        net = self.system.street_network(num_intersections=15, seed=21)
        levels = {e["level"] for e in net["edges"]}
        assert {"arterial", "collector", "local"} <= levels
        arterials = [e for e in net["edges"] if e["level"] == "arterial"]
        locals_ = [e for e in net["edges"] if e["level"] == "local"]
        assert arterials and locals_
        assert max(e["length"] for e in arterials) >= max(e["length"] for e in locals_)

    # ---- street_network: 有机（不是直线） ----
    def test_case_13(self):
        net = self.system.street_network(num_intersections=10, seed=22)
        curved = 0
        for edge in net["edges"]:
            p0, p1 = edge["path"][0], edge["path"][-1]
            assert len(edge["path"]) >= 3
            for mx, my in edge["path"][1:-1]:
                cross = (p1[0] - p0[0]) * (my - p0[1]) - (p1[1] - p0[1]) * (mx - p0[0])
                if abs(cross) > 1e-6:
                    curved += 1
                    break
        assert curved >= len(net["edges"]) * 0.9

    # ---- building_detail: 装饰 ----
    def test_case_14(self):
        building = self.system.generate_building(floors=8, seed=30)
        details = building["details"]
        assert details["decorations"], "建筑必须有装饰细节"
        allowed = {"balcony", "chimney", "ac_unit", "awning", "roof_garden",
                   "antenna", "dormer", "fire_escape"}
        for deco in details["decorations"]:
            assert deco["type"] in allowed
            assert deco["count"] >= 1 and deco["floors"]

    # ---- building_detail: 每栋不一样 ----
    def test_case_15(self):
        sigs = set()
        for seed in range(10):
            d = self.system.generate_building(floors=10, seed=100 + seed)["details"]
            sig = tuple(
                (x["type"], tuple(x["floors"])) for x in d["decorations"]
            )
            sigs.add(sig)
        assert len(sigs) > 1, "建筑细节必须有变化"

    # ---- building_detail: 不再是方块（立面分段） ----
    def test_case_16(self):
        building = self.system.generate_building(floors=6, seed=40)
        facade = building["details"]["facade"]
        assert len(facade) >= 2
        assert all(seg["material"] and seg["color"] for seg in facade)
        # 完整建筑同时包含楼层、户型、风格、细节
        assert building["floors"] and building["style"]["roof"]
        assert building["details"]["decorations"] or len(facade) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
