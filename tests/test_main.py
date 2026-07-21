from __future__ import annotations

import io
import json
import tempfile
import unittest
from collections import defaultdict
from collections.abc import Sequence
from contextlib import redirect_stdout
from pathlib import Path

import main


class ScaleStationCoordinatesTests(unittest.TestCase):
    def test_scale_station_coordinates_scales_values_without_mutating_input(
        self,
    ) -> None:
        data = {"stations": {"a": {"x": 10, "y": 20}}}

        scaled = main.scale_station_coordinates(data, 1.5)

        self.assertEqual(scaled["stations"]["a"]["x"], 15.0)
        self.assertEqual(scaled["stations"]["a"]["y"], 30.0)
        self.assertEqual(data["stations"]["a"]["x"], 10)
        self.assertEqual(data["stations"]["a"]["y"], 20)

    def test_scale_station_coordinates_rejects_non_positive_scale(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            main.scale_station_coordinates({"stations": {}}, 0)


class RenderCommandTests(unittest.TestCase):
    def test_render_map_calls_renderer_with_scaled_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            output_path = Path(temp_dir) / "preview.png"
            data_path.write_text(
                json.dumps({"stations": {"s1": {"x": 2, "y": 4}}, "lines": {}}),
                encoding="utf-8",
            )

            renderer_calls: list[tuple[dict[str, object], str]] = []

            def renderer(
                data: dict[str, object],
                output: str,
                background: str | None,
                fonts: list[str] | None,
            ) -> None:
                _ = background, fonts
                renderer_calls.append((data, output))

            success = main.render_map(
                data_path=data_path,
                output_path=output_path,
                scale=2.0,
                font_paths=["font-a.ttf"],
                renderer=renderer,
            )

        self.assertTrue(success)
        self.assertEqual(renderer_calls[0][0]["stations"], {"s1": {"x": 4.0, "y": 8.0}})
        self.assertEqual(renderer_calls[0][1], str(output_path))

    def test_render_map_svg_mode_writes_svg_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            output_path = Path(temp_dir) / "preview.png"
            data_path.write_text(
                json.dumps({"stations": {"s1": {"x": 2, "y": 4}}, "lines": {}}),
                encoding="utf-8",
            )
            renderer_calls: list[str] = []

            def renderer(
                data: dict[str, object],
                output: str,
                background: str | None,
                fonts: list[str] | None,
            ) -> None:
                _ = data, background, fonts
                renderer_calls.append(output)
                Path(output).write_text("<svg />", encoding="utf-8")

            success = main.render_map(
                data_path=data_path,
                output_path=output_path,
                mode="svg",
                renderer=renderer,
            )

            self.assertTrue(success)
            self.assertEqual(renderer_calls, [str(output_path.with_suffix(".svg"))])
            self.assertTrue(output_path.with_suffix(".svg").exists())

    def test_render_map_svg_png_mode_converts_temporary_svg(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            output_path = Path(temp_dir) / "preview.png"
            data_path.write_text(
                json.dumps({"stations": {"s1": {"x": 2, "y": 4}}, "lines": {}}),
                encoding="utf-8",
            )
            renderer_calls: list[str] = []
            converter_calls: list[tuple[Path, Path]] = []

            def renderer(
                data: dict[str, object],
                output: str,
                background: str | None,
                fonts: list[str] | None,
            ) -> None:
                _ = data, background, fonts
                renderer_calls.append(output)
                Path(output).write_text("<svg />", encoding="utf-8")

            def converter(svg_path: Path, png_path: Path) -> None:
                converter_calls.append((svg_path, png_path))
                png_path.write_bytes(b"png")

            success = main.render_map(
                data_path=data_path,
                output_path=output_path,
                mode="svg-png",
                renderer=renderer,
                svg_png_converter=converter,
            )

            temporary_svg_path = output_path.with_suffix(output_path.suffix + ".svg")
            self.assertTrue(success)
            self.assertEqual(renderer_calls, [str(temporary_svg_path)])
            self.assertEqual(converter_calls, [(temporary_svg_path, output_path)])
            self.assertTrue(output_path.exists())
            self.assertFalse(temporary_svg_path.exists())

    def test_watch_render_regenerates_when_timestamp_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            output_path = Path(temp_dir) / "preview.png"
            data_path.write_text(
                json.dumps({"stations": {"s1": {"x": 1, "y": 2}}, "lines": {}}),
                encoding="utf-8",
            )

            renderer_calls: list[str] = []

            def renderer(
                data: dict[str, object],
                output: str,
                background: str | None,
                fonts: list[str] | None,
            ) -> None:
                _ = data, background, fonts
                renderer_calls.append(output)

            def fake_sleep(seconds: float) -> None:
                _ = seconds

            def render_and_touch(
                data_path_arg: Path,
                output_path_arg: Path,
                background_path: Path | None = None,
                font_paths: Sequence[str] | None = None,
                scale: float = 1.0,
                mode: str = "pil",
                renderer_func: main.Renderer = main.draw_metro_map,
            ) -> bool:
                result = main.render_map(
                    data_path_arg,
                    output_path_arg,
                    background_path,
                    font_paths,
                    scale,
                    mode,
                    renderer_func,
                )
                if len(renderer_calls) == 1:
                    data_path.write_text(
                        json.dumps({"stations": {"s1": {"x": 9, "y": 3}}, "lines": {}}),
                        encoding="utf-8",
                    )
                return result

            main.watch_render(
                data_path=data_path,
                output_path=output_path,
                interval=0,
                font_paths=["font-a.ttf"],
                renderer=renderer,
                render_func=render_and_touch,
                sleep_func=fake_sleep,
                max_iterations=3,
            )

        self.assertEqual(renderer_calls, [str(output_path), str(output_path)])


class BoundsCommandTests(unittest.TestCase):
    def test_calculate_bounds_returns_min_max_coordinates(self) -> None:
        bounds = main.calculate_bounds(
            {
                "stations": {
                    "a": {"x": 10, "y": 30},
                    "b": {"x": -5, "y": 7.5},
                    "c": {"x": 18, "y": 0},
                }
            }
        )

        self.assertEqual(bounds, (-5.0, 18.0, 0.0, 30.0))

    def test_main_bounds_command_reads_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            data_path.write_text(
                json.dumps({"stations": {"a": {"x": 1, "y": 2}}}),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main.main(["bounds", str(data_path)])

        self.assertEqual(exit_code, 0)
        self.assertIn("min_x: 1.0", output.getvalue())

    def test_main_render_command_returns_failure_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.json"
            output_path = Path(temp_dir) / "preview.png"

            with redirect_stdout(io.StringIO()) as output:
                exit_code = main.main(
                    ["render", str(missing_path), "--output", str(output_path)]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("Data file not found", output.getvalue())


class MapPackageTests(unittest.TestCase):
    def test_load_map_data_supports_single_json_with_train_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            data_path.write_text(
                json.dumps(
                    {
                        "id": "demo",
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "trainInfo": {"rollingStockRefs": ["t-a"]},
                            }
                        },
                        "trains": {"t-a": {"model": "Type A Demo"}},
                    }
                ),
                encoding="utf-8",
            )

            data = main.load_map_data(data_path)

        self.assertEqual(data["id"], "demo")
        self.assertIn("t-a", data["trains"])
        self.assertEqual(
            data["lines"]["l1"]["trainInfo"], {"rollingStockRefs": ["t-a"]}
        )

    def test_load_map_data_rejects_unknown_train_reference_in_single_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            data_path.write_text(
                json.dumps(
                    {
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "trainInfo": {"rollingStockRefs": ["missing-train"]},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Unknown train id"):
                main.load_map_data(data_path)

    def test_load_map_data_rejects_non_reference_train_fields_in_single_json(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "map.json"
            data_path.write_text(
                json.dumps(
                    {
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "trainInfo": {
                                    "rollingStockRefs": ["t-a"],
                                    "formation": {"cars": 6},
                                },
                            }
                        },
                        "trains": {"t-a": {"model": "Type A Demo"}},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError, "trainInfo only supports rollingStockRefs"
            ):
                main.load_map_data(data_path)

    def test_load_map_data_supports_directory_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "sample_map"
            (package_dir / "stations").mkdir(parents=True)
            (package_dir / "lines").mkdir(parents=True)
            (package_dir / "connections").mkdir(parents=True)

            (package_dir / "map.json").write_text(
                json.dumps({"id": "demo", "meta": {"author": "tester"}}),
                encoding="utf-8",
            )
            (package_dir / "stations" / "core.json").write_text(
                json.dumps(
                    {"stations": {"s1": {"x": 1, "y": 2}, "s2": {"x": 3, "y": 4}}}
                ),
                encoding="utf-8",
            )
            (package_dir / "lines" / "metro.json").write_text(
                json.dumps({"lines": {"l1": {"id": "l1", "stations": ["s1", "s2"]}}}),
                encoding="utf-8",
            )
            (package_dir / "connections" / "transfers.json").write_text(
                json.dumps(
                    {
                        "connections": [
                            {
                                "fromStationId": "s1",
                                "toStationId": "s2",
                                "type": "physical",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            data = main.load_map_data(package_dir)

        self.assertEqual(data["id"], "demo")
        self.assertEqual(sorted(data["stations"].keys()), ["s1", "s2"])
        self.assertEqual(list(data["lines"].keys()), ["l1"])
        self.assertEqual(len(data["connections"]), 1)

    def test_load_map_data_preserves_line_metadata_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "sample_map"
            (package_dir / "lines").mkdir(parents=True)
            (package_dir / "lines" / "metro.json").write_text(
                json.dumps(
                    {
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "stations": ["s1", "s2"],
                                "lineInfo": {
                                    "operator": {"zh-CN": "示例公司"},
                                    "maxOperatingSpeedKmh": 80,
                                    "operationFeatures": {"ato": True},
                                },
                                "trainInfo": {"rollingStockRefs": ["t-a"]},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (package_dir / "trains").mkdir(parents=True)
            (package_dir / "trains" / "t-a.json").write_text(
                json.dumps({"trains": {"t-a": {"model": "Type A Demo"}}}),
                encoding="utf-8",
            )

            data = main.load_map_data(package_dir)

        self.assertEqual(
            data["lines"]["l1"]["lineInfo"]["operator"]["zh-CN"], "示例公司"
        )
        self.assertEqual(data["lines"]["l1"]["lineInfo"]["maxOperatingSpeedKmh"], 80)
        self.assertEqual(data["lines"]["l1"]["trainInfo"]["rollingStockRefs"], ["t-a"])
        self.assertTrue(data["lines"]["l1"]["lineInfo"]["operationFeatures"]["ato"])

    def test_load_map_data_preserves_train_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "sample_map"
            (package_dir / "lines").mkdir(parents=True)
            (package_dir / "trains").mkdir(parents=True)
            (package_dir / "lines" / "metro.json").write_text(
                json.dumps(
                    {
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "stations": ["s1", "s2"],
                                "trainInfo": {"rollingStockRefs": ["t-a"]},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (package_dir / "trains" / "t-a.json").write_text(
                json.dumps(
                    {
                        "trains": {
                            "t-a": {
                                "model": "Type A Demo",
                                "carCount": 6,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            data = main.load_map_data(package_dir)

        self.assertIn("trains", data)
        self.assertIn("t-a", data["trains"])
        self.assertEqual(
            data["lines"]["l1"]["trainInfo"]["rollingStockRefs"],
            ["t-a"],
        )
        self.assertEqual(
            data["lines"]["l1"]["trainInfo"], {"rollingStockRefs": ["t-a"]}
        )

    def test_load_map_data_rejects_unknown_train_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "sample_map"
            (package_dir / "lines").mkdir(parents=True)
            (package_dir / "lines" / "metro.json").write_text(
                json.dumps(
                    {
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "trainInfo": {"rollingStockRefs": ["missing-train"]},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Unknown train id"):
                main.load_map_data(package_dir)

    def test_load_map_data_rejects_non_reference_train_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "sample_map"
            (package_dir / "lines").mkdir(parents=True)
            (package_dir / "lines" / "metro.json").write_text(
                json.dumps(
                    {
                        "lines": {
                            "l1": {
                                "id": "l1",
                                "trainInfo": {
                                    "rollingStockRefs": ["t-a"],
                                    "formation": {"cars": 6},
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (package_dir / "trains").mkdir(parents=True)
            (package_dir / "trains" / "t-a.json").write_text(
                json.dumps({"trains": {"t-a": {"model": "Type A Demo"}}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError, "trainInfo only supports rollingStockRefs"
            ):
                main.load_map_data(package_dir)

    def test_load_map_data_rejects_duplicate_station_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "sample_map"
            (package_dir / "stations").mkdir(parents=True)
            (package_dir / "stations" / "a.json").write_text(
                json.dumps({"stations": {"s1": {"x": 1, "y": 2}}}),
                encoding="utf-8",
            )
            (package_dir / "stations" / "b.json").write_text(
                json.dumps({"stations": {"s1": {"x": 3, "y": 4}}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Duplicate station id"):
                main.load_map_data(package_dir)

    def test_pack_and_unpack_map_package_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            package_dir = temp_path / "sample_map"
            archive_path = temp_path / "sample_map.zip"
            unpack_dir = temp_path / "unpacked_map"
            (package_dir / "stations").mkdir(parents=True)
            (package_dir / "map.json").write_text(
                json.dumps({"id": "demo", "meta": {"author": "tester"}}),
                encoding="utf-8",
            )
            (package_dir / "stations" / "core.json").write_text(
                json.dumps({"stations": {"s1": {"x": 1, "y": 2}}}),
                encoding="utf-8",
            )

            pack_exit_code = main.main(
                ["pack", str(package_dir), "--output", str(archive_path)]
            )
            unpack_exit_code = main.main(
                ["unpack", str(archive_path), "--output", str(unpack_dir)]
            )
            unpacked_data = main.load_map_data(unpack_dir)

            self.assertEqual(pack_exit_code, 0)
            self.assertEqual(unpack_exit_code, 0)
            self.assertTrue(archive_path.exists())
            self.assertEqual(unpacked_data["id"], "demo")
            self.assertIn("s1", unpacked_data["stations"])

    def test_load_map_data_supports_repository_gz_package(self) -> None:
        data = main.load_map_data(Path("library/gz"))

        self.assertEqual(data["id"], "gzm")
        self.assertIn("101", data["stations"])
        self.assertIn("1", data["lines"])
        self.assertIn("gz-b7", data["trains"])
        self.assertGreater(len(data["connections"]), 0)

    def test_repository_gz_trains_do_not_use_shared_file(self) -> None:
        self.assertFalse(Path("library/gz/trains/shared.json").exists())

    def test_repository_gz_train_files_define_single_train(self) -> None:
        trains_dir = Path("library/gz/trains")

        for train_file in trains_dir.glob("*.json"):
            with self.subTest(train_file=train_file.name):
                payload = json.loads(train_file.read_text(encoding="utf-8"))
                self.assertIn("trains", payload)
                self.assertEqual(len(payload["trains"]), 1)

    def test_repository_gz_lines_include_line_and_train_metadata(self) -> None:
        data = main.load_map_data(Path("library/gz"))

        expected_lines = {
            "1",
            "2",
            "3",
            "3B",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "14B",
            "18",
            "21",
            "22",
            "APM",
            "GF",
            "F2",
            "F3",
            "TNH1",
        }

        self.assertTrue(expected_lines.issubset(data["lines"].keys()))

        for line_id in expected_lines:
            with self.subTest(line_id=line_id):
                line = data["lines"][line_id]
                self.assertIn("lineInfo", line)
                self.assertIn("trainInfo", line)
                self.assertEqual(set(line["trainInfo"].keys()), {"rollingStockRefs"})

    def test_repository_gz_researched_line_and_train_metadata(self) -> None:
        data = main.load_map_data(Path("library/gz"))

        self.assertEqual(data["lines"]["2"]["lineInfo"]["maxOperatingSpeedKmh"], 80)
        self.assertEqual(
            data["lines"]["2"]["trainInfo"]["rollingStockRefs"],
            ["gz-a4", "gz-a5"],
        )

        self.assertEqual(data["lines"]["4"]["lineInfo"]["maxOperatingSpeedKmh"], 90)
        self.assertEqual(
            data["lines"]["4"]["trainInfo"]["rollingStockRefs"],
            ["gz-l1", "gz-l5"],
        )

        self.assertEqual(
            data["lines"]["10"]["lineInfo"]["signalling"], "TieKe Zhikong MTC-I"
        )
        self.assertEqual(
            data["lines"]["10"]["trainInfo"]["rollingStockRefs"],
            ["gz-b13"],
        )
        self.assertEqual(
            data["lines"]["10"]["lineInfo"]["operationFeatures"]["driverlessGrade"],
            "GoA4",
        )

        self.assertEqual(data["lines"]["11"]["lineInfo"]["maxOperatingSpeedKmh"], 80)
        self.assertEqual(
            data["lines"]["11"]["trainInfo"]["rollingStockRefs"],
            ["gz-a9"],
        )

        self.assertEqual(
            data["lines"]["1"]["trainInfo"]["rollingStockRefs"],
            ["gz-a1", "gz-a2", "gz-a3"],
        )

        self.assertEqual(data["lines"]["7"]["lineInfo"]["maxOperatingSpeedKmh"], 80)
        self.assertEqual(
            data["lines"]["7"]["trainInfo"]["rollingStockRefs"],
            ["gz-b5", "gz-b9", "gz-b12"],
        )
        self.assertEqual(
            data["lines"]["7"]["lineInfo"]["operationFeatures"]["driverlessGrade"],
            "GoA3",
        )

        self.assertEqual(
            data["lines"]["8"]["lineInfo"]["signalling"],
            "Siemens Trainguard LZB 700 M / FTGS",
        )
        self.assertEqual(
            data["lines"]["8"]["trainInfo"]["rollingStockRefs"],
            ["gz-a2", "gz-a5", "gz-a6", "gz-a8"],
        )

        self.assertEqual(data["lines"]["9"]["lineInfo"]["maxOperatingSpeedKmh"], 120)
        self.assertEqual(
            data["lines"]["9"]["trainInfo"]["rollingStockRefs"],
            ["gz-b6"],
        )

        self.assertEqual(data["lines"]["12"]["lineInfo"]["maxOperatingSpeedKmh"], 80)
        self.assertEqual(
            data["lines"]["12"]["trainInfo"]["rollingStockRefs"],
            ["gz-a10"],
        )
        self.assertEqual(
            data["lines"]["12"]["lineInfo"]["operationFeatures"]["driverlessGrade"],
            "GoA4",
        )

        self.assertEqual(data["lines"]["13"]["lineInfo"]["maxOperatingSpeedKmh"], 100)
        self.assertEqual(
            data["lines"]["13"]["trainInfo"]["rollingStockRefs"],
            ["gz-a7", "gz-a11"],
        )

        self.assertEqual(
            data["lines"]["14"]["trainInfo"]["rollingStockRefs"],
            ["gz-b7", "gz-b8", "gz-b14"],
        )
        self.assertEqual(
            data["lines"]["14B"]["trainInfo"]["rollingStockRefs"],
            ["gz-b14"],
        )
        self.assertEqual(
            data["lines"]["18"]["trainInfo"]["rollingStockRefs"],
            ["gz-d1", "gz-d2"],
        )
        self.assertEqual(
            data["lines"]["GF"]["trainInfo"]["rollingStockRefs"],
            ["gf-b3", "gf-b3i", "gf-sfm77"],
        )
        self.assertEqual(
            data["lines"]["F2"]["trainInfo"]["rollingStockRefs"],
            ["fs-sfm53"],
        )
        self.assertEqual(
            data["lines"]["F3"]["trainInfo"]["rollingStockRefs"],
            ["fs-sfm105"],
        )

    def test_repository_gz_descriptive_train_names_are_documented(self) -> None:
        data = main.load_map_data(Path("library/gz"))

        f3_train = data["trains"]["fs-sfm105"]
        self.assertEqual(f3_train["model"], "SFM105")
        self.assertIn("暂未取得足够稳定的一手官方编号来源", f3_train["notes"]["zh-CN"])

        tnh1_train = data["trains"]["tnh1-tram-3"]
        self.assertEqual(tnh1_train["model"], "三模块有轨电车")
        self.assertIn("暂用描述性车型名", tnh1_train["notes"]["zh-CN"])

    def test_repository_gz_station_lines_and_transfer_flags_match_drawn_lines(
        self,
    ) -> None:
        data = main.load_map_data(Path("library/gz"))

        station_to_lines: dict[str, list[str]] = defaultdict(list)
        for line_id, line in data["lines"].items():
            for item in line.get("stations", []):
                status = "active"
                if isinstance(item, str):
                    station_id = item
                else:
                    station_id = item["id"]
                    status = item.get("status", "active")

                if status in {"pass", "deferred"}:
                    continue

                station_to_lines[station_id].append(line_id)

        for station_id, station in data["stations"].items():
            with self.subTest(station_id=station_id):
                expected_lines = list(
                    dict.fromkeys(station_to_lines.get(station_id, []))
                )
                self.assertEqual(station.get("lines", []), expected_lines)
                self.assertEqual(
                    station.get("isTransfer", False), len(expected_lines) >= 2
                )


if __name__ == "__main__":
    unittest.main()
