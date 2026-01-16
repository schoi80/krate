import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import pytest

from dj_playlist_optimizer import rekordbox
from dj_playlist_optimizer.models import PlaylistResult, Track


# Sample data for tests
@pytest.fixture
def sample_tracks():
    return [
        Track(
            id="1",
            key="1A",
            bpm=120.0,
            title="Track 1",
            artist="Artist 1",
            path="/music/t1.mp3",
            rekordbox_id=101,
        ),
        Track(
            id="2",
            key="1B",
            bpm=124.0,
            title="Track 2",
            artist="Artist 2",
            path="/music/t2.mp3",
            rekordbox_id=102,
        ),
    ]


@pytest.fixture
def playlist_result(sample_tracks):
    return PlaylistResult(playlist=sample_tracks)


class TestRekordboxLoader:
    def test_init_no_pyrekordbox(self):
        with (
            patch("dj_playlist_optimizer.rekordbox.HAS_PYREKORDBOX", False),
            pytest.raises(ImportError, match="pyrekordbox is not installed"),
        ):
            rekordbox.RekordboxLoader()

    def test_init_db_error(self):
        with (
            patch("dj_playlist_optimizer.rekordbox.HAS_PYREKORDBOX", True),
            patch(
                "dj_playlist_optimizer.rekordbox.Rekordbox6Database",
                side_effect=Exception("DB Locked"),
            ),
            pytest.raises(RuntimeError, match="Failed to initialize Rekordbox database"),
        ):
            rekordbox.RekordboxLoader()

    def test_list_playlists(self):
        with patch("dj_playlist_optimizer.rekordbox.HAS_PYREKORDBOX", True):
            mock_db = MagicMock()

            # Mock playlist objects
            p1 = MagicMock()
            p1.ID = "100"
            p1.Name = "Techno"
            p1.Songs = ["s1", "s2"]  # Len 2

            p2 = MagicMock()
            p2.Name = "ROOT"  # Should be skipped

            p3 = MagicMock()
            p3.ID = "101"
            p3.Name = "House"
            # No Songs attr, should handle gracefully
            del p3.Songs

            mock_db.get_playlist.return_value = [p1, p2, p3]

            with patch("dj_playlist_optimizer.rekordbox.Rekordbox6Database", return_value=mock_db):
                loader = rekordbox.RekordboxLoader()
                playlists = loader.list_playlists()

                assert len(playlists) == 2
                assert playlists[0].name == "Techno"
                assert playlists[0].count == 2
                assert playlists[1].name == "House"
                assert playlists[1].count == 0

    def test_get_tracks(self):
        with patch("dj_playlist_optimizer.rekordbox.HAS_PYREKORDBOX", True):
            mock_db = MagicMock()

            # Mock playlist
            pl = MagicMock()
            pl.Name = "My Playlist"

            # Mock songs
            song1 = MagicMock()
            song1.Content.Title = "Song A"
            song1.Content.Artist.Name = "Artist A"
            song1.Content.BPM = 12000  # 120.00
            song1.Content.KeyName = "8A"  # Camelot
            song1.Content.Rating = 4
            song1.Content.Length = 180
            song1.Content.FolderPath = "/path/to/a.mp3"
            song1.Content.ID = 1001

            song2 = MagicMock()
            song2.Content.Title = "Song B"
            song2.Content.Artist = None  # Unknown artist
            song2.Content.BPM = 124  # Direct float/int? Code handles > 200 check
            song2.Content.KeyName = None  # Ensure fallback
            song2.Content.Tonality = "Fm"  # Standard notation -> 4A
            song2.Content.ID = 1002

            # Song 3 - Invalid (No key)
            song3 = MagicMock()
            song3.Content.KeyName = None
            song3.Content.Tonality = None

            pl.Songs = [song1, song2, song3]

            mock_db.get_playlist.return_value = [pl]

            with patch("dj_playlist_optimizer.rekordbox.Rekordbox6Database", return_value=mock_db):
                loader = rekordbox.RekordboxLoader()
                tracks = loader.get_tracks("My Playlist")

                assert len(tracks) == 2

                t1 = tracks[0]
                assert t1.id == "Artist A - Song A"
                assert t1.bpm == 120.0
                assert t1.key == "8A"
                assert t1.path == "/path/to/a.mp3"
                assert t1.rekordbox_id == 1001

                t2 = tracks[1]
                assert t2.id == "Unknown - Song B"
                assert t2.bpm == 124.0  # Code: if > 200 div 100. 124 <= 200, so 124.0
                assert t2.key == "4A"  # Fm -> 4A

                # Test playlist not found
                with pytest.raises(ValueError, match="Playlist 'Missing' not found"):
                    loader.get_tracks("Missing")

    def test_write_playlist_to_db(self, playlist_result):
        with patch("dj_playlist_optimizer.rekordbox.HAS_PYREKORDBOX", True):
            mock_db = MagicMock()
            new_pl = MagicMock()
            mock_db.create_playlist.return_value = new_pl

            # Mock get_content
            mock_db.get_content.side_effect = lambda **kwargs: (
                MagicMock() if kwargs.get("ID") == 101 else None
            )

            with patch("dj_playlist_optimizer.rekordbox.Rekordbox6Database", return_value=mock_db):
                loader = rekordbox.RekordboxLoader()

                # Modify one track to have no ID
                playlist_result.playlist[1].rekordbox_id = None

                loader.write_playlist_to_db(playlist_result, "New PL")

                mock_db.create_playlist.assert_called_with("New PL")
                # Only first track has ID 101 and exists
                assert mock_db.add_to_playlist.call_count == 1
                mock_db.commit.assert_called_once()

    def test_write_playlist_to_db_failure(self, playlist_result):
        with patch("dj_playlist_optimizer.rekordbox.HAS_PYREKORDBOX", True):
            mock_db = MagicMock()
            mock_db.create_playlist.side_effect = RuntimeError("Fail create")

            with patch("dj_playlist_optimizer.rekordbox.Rekordbox6Database", return_value=mock_db):
                loader = rekordbox.RekordboxLoader()
                with pytest.raises(RuntimeError, match="Failed to create playlist"):
                    loader.write_playlist_to_db(playlist_result, "Fail")


class TestRekordboxXML:
    def test_write_rekordbox_xml(self, playlist_result, tmp_path):
        output_file = tmp_path / "test_export.xml"
        rekordbox.write_rekordbox_xml(playlist_result, "SourcePL", output_file)

        assert output_file.exists()

        tree = ET.parse(output_file)
        root = tree.getroot()

        assert root.tag == "DJ_PLAYLISTS"

        collection = root.find("COLLECTION")
        assert collection is not None
        assert len(collection) == 2

        # Check track 1
        t1 = collection.find("./TRACK[@TrackID='1']")
        assert t1 is not None
        assert t1.get("Name") == "Track 1"
        assert t1.get("AverageBpm") == "120.0"
        assert t1.get("Location") == "file://localhost/music/t1.mp3"

        playlists = root.find("PLAYLISTS")
        assert playlists is not None
        pl_node = playlists.find(".//NODE[@Type='1']")
        assert pl_node is not None
        assert pl_node.get("Name", "").startswith("SourcePL_")
        assert len(pl_node) == 2

        # Check track ref
        ref1 = pl_node.find("./TRACK[@Key='1']")
        assert ref1 is not None
