import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from djkr8 import PlaylistResult, PlaylistStatistics, Track, cli


@pytest.fixture
def mock_tracks_json(tmp_path):
    f = tmp_path / "tracks.json"
    data = {
        "tracks": [
            {"id": "t1", "key": "1A", "bpm": 120},
            {"id": "t2", "key": "1A", "bpm": 120},
            {"id": "t3", "key": "2A", "bpm": 122},
        ]
    }
    with open(f, "w") as fp:
        json.dump(data, fp)
    return f


@pytest.fixture
def mock_optimizer():
    with patch("djkr8.cli.PlaylistOptimizer") as mock_opt:
        instance = mock_opt.return_value
        # Default successful result
        instance.optimize.return_value = PlaylistResult(
            playlist=[Track(id="t1", key="1A", bpm=120), Track(id="t2", key="1A", bpm=120)],
            solver_status="OPTIMAL",
            solver_time_seconds=0.1,
            statistics=PlaylistStatistics(
                total_input_tracks=3,
                playlist_length=2,
                harmonic_transitions=1,
                non_harmonic_transitions=0,
                avg_bpm=120.0,
                bpm_range=(120.0, 120.0),
            ),
        )
        yield mock_opt


class TestCLI:
    def test_load_tracks_from_json(self, mock_tracks_json):
        tracks = cli.load_tracks_from_json(mock_tracks_json)
        assert len(tracks) == 3
        assert tracks[0].id == "t1"

    def test_load_tracks_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        with open(f, "w") as fp:
            fp.write('{"tracks": "not_a_list"}')

        with pytest.raises(ValueError, match="must contain a 'tracks' array"):
            cli.load_tracks_from_json(f)

    def test_load_tracks_missing_fields(self, tmp_path):
        f = tmp_path / "missing.json"
        with open(f, "w") as fp:
            fp.write('{"tracks": [{"id": "t1"}]}')  # Missing key/bpm

        with pytest.raises(ValueError, match="Track missing required fields"):
            cli.load_tracks_from_json(f)

    def test_main_basic_flow(self, mock_tracks_json, mock_optimizer, capsys):
        with patch.object(sys, "argv", ["dj-optimize", str(mock_tracks_json)]):
            ret = cli.main()
            assert ret == 0
            captured = capsys.readouterr()
            assert "Found playlist with 2 tracks" in captured.out

    def test_main_with_args(self, mock_tracks_json, mock_optimizer):
        with patch.object(
            sys,
            "argv",
            [
                "dj-optimize",
                str(mock_tracks_json),
                "--bpm-tolerance",
                "5",
                "--no-halftime",
                "--harmonic-level",
                "relaxed",
                "--start",
                "t1",
            ],
        ):
            ret = cli.main()
            assert ret == 0

            # verify optimizer init
            mock_optimizer.assert_called_once()
            _, kwargs = mock_optimizer.call_args
            assert kwargs["bpm_tolerance"] == 5.0
            assert kwargs["allow_halftime_bpm"] is False
            assert kwargs["harmonic_level"] == "relaxed"

            # verify optimize call
            instance = mock_optimizer.return_value
            instance.optimize.assert_called_once()
            _, kwargs = instance.optimize.call_args
            assert kwargs["start_track_id"] == "t1"

    def test_main_output_json(self, mock_tracks_json, mock_optimizer, tmp_path):
        out = tmp_path / "out.json"
        with patch.object(sys, "argv", ["dj-optimize", str(mock_tracks_json), "-o", str(out)]):
            ret = cli.main()
            assert ret == 0
            assert out.exists()

    def test_main_rekordbox_flow(self, mock_optimizer):
        with (
            patch("djkr8.cli.HAS_PYREKORDBOX", True),
            patch("djkr8.cli.RekordboxLoader") as mock_loader,
        ):
            # Setup loader mock
            pl1 = MagicMock()
            pl1.name = "Techno"
            pl1.count = 10

            pl2 = MagicMock()
            pl2.name = "House"
            pl2.count = 5

            loader = mock_loader.return_value
            loader.list_playlists.return_value = [pl1, pl2]
            loader.get_tracks.return_value = [Track(id="t1", key="1A", bpm=120)]

            # Test listing
            with patch.object(sys, "argv", ["dj-optimize", "--rekordbox"]):
                ret = cli.main()
                assert ret == 0
                loader.list_playlists.assert_called_once()

            # Test optimization
            with patch.object(sys, "argv", ["dj-optimize", "--rekordbox", "--playlist", "Techno"]):
                ret = cli.main()
                assert ret == 0
                loader.get_tracks.assert_called_with("Techno")

    def test_main_rekordbox_write_db(self, mock_optimizer):
        with (
            patch("djkr8.cli.HAS_PYREKORDBOX", True),
            patch("djkr8.cli.RekordboxLoader") as mock_loader,
        ):
            loader = mock_loader.return_value
            loader.get_tracks.return_value = [Track(id="t1", key="1A", bpm=120)]

            with patch.object(
                sys,
                "argv",
                ["dj-optimize", "--rekordbox", "--playlist", "Techno", "--write-to-db"],
            ):
                ret = cli.main()
                assert ret == 0
                loader.write_playlist_to_db.assert_called_once()

    def test_main_rekordbox_xml_export(self, mock_optimizer, tmp_path):
        out_xml = tmp_path / "out.xml"
        with (
            patch("djkr8.cli.HAS_PYREKORDBOX", True),
            patch("djkr8.cli.RekordboxLoader") as mock_loader,
        ):
            loader = mock_loader.return_value
            loader.get_tracks.return_value = [Track(id="t1", key="1A", bpm=120)]

            with (
                patch("djkr8.cli.write_rekordbox_xml") as mock_write,
                patch.object(
                    sys,
                    "argv",
                    ["dj-optimize", "--rekordbox", "--playlist", "Techno", "-o", str(out_xml)],
                ),
            ):
                ret = cli.main()
                assert ret == 0
                mock_write.assert_called_once()

    def test_main_no_solution(self, mock_tracks_json):
        # Force empty result
        with patch("djkr8.cli.PlaylistOptimizer") as mock_opt:
            instance = mock_opt.return_value
            instance.optimize.return_value = PlaylistResult(playlist=[], solver_status="INFEASIBLE")

            with patch.object(sys, "argv", ["dj-optimize", str(mock_tracks_json)]):
                ret = cli.main()
                assert ret == 1
