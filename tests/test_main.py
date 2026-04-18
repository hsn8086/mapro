from __future__ import annotations

import io
import json
import tempfile
import unittest
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
                renderer_func: main.Renderer = main.draw_metro_map,
            ) -> bool:
                result = main.render_map(
                    data_path_arg,
                    output_path_arg,
                    background_path,
                    font_paths,
                    scale,
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
                                },
                                "trainInfo": {
                                    "formation": {"cars": 6},
                                    "serviceFeatures": {"ato": True},
                                },
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            data = main.load_map_data(package_dir)

        self.assertEqual(
            data["lines"]["l1"]["lineInfo"]["operator"]["zh-CN"], "示例公司"
        )
        self.assertEqual(data["lines"]["l1"]["lineInfo"]["maxOperatingSpeedKmh"], 80)
        self.assertEqual(data["lines"]["l1"]["trainInfo"]["formation"]["cars"], 6)
        self.assertTrue(data["lines"]["l1"]["trainInfo"]["serviceFeatures"]["ato"])

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
        self.assertGreater(len(data["connections"]), 0)

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


if __name__ == "__main__":
    unittest.main()
