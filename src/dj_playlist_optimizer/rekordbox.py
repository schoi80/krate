"""Rekordbox 6 database loader and XML exporter."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from dj_playlist_optimizer.models import PlaylistResult, Track

try:
    from pyrekordbox import Rekordbox6Database

    HAS_PYREKORDBOX = True
except ImportError:
    HAS_PYREKORDBOX = False
    Rekordbox6Database = None

logger = logging.getLogger(__name__)


# Mapping from standard musical keys to Camelot notation
KEY_MAPPING = {
    # Major Keys
    "B": "1B",
    "B Major": "1B",
    "B Maj": "1B",
    "F#": "2B",
    "F# Major": "2B",
    "F# Maj": "2B",
    "Gb": "2B",
    "Gb Major": "2B",
    "Gb Maj": "2B",
    "Db": "3B",
    "Db Major": "3B",
    "Db Maj": "3B",
    "C#": "3B",
    "C# Major": "3B",
    "C# Maj": "3B",
    "Ab": "4B",
    "Ab Major": "4B",
    "Ab Maj": "4B",
    "G#": "4B",
    "G# Major": "4B",
    "G# Maj": "4B",
    "Eb": "5B",
    "Eb Major": "5B",
    "Eb Maj": "5B",
    "D#": "5B",
    "D# Major": "5B",
    "D# Maj": "5B",
    "Bb": "6B",
    "Bb Major": "6B",
    "Bb Maj": "6B",
    "A#": "6B",
    "A# Major": "6B",
    "A# Maj": "6B",
    "F": "7B",
    "F Major": "7B",
    "F Maj": "7B",
    "C": "8B",
    "C Major": "8B",
    "C Maj": "8B",
    "G": "9B",
    "G Major": "9B",
    "G Maj": "9B",
    "D": "10B",
    "D Major": "10B",
    "D Maj": "10B",
    "A": "11B",
    "A Major": "11B",
    "A Maj": "11B",
    "E": "12B",
    "E Major": "12B",
    "E Maj": "12B",
    # Minor Keys
    "Abm": "1A",
    "Ab Minor": "1A",
    "Ab Min": "1A",
    "G#m": "1A",
    "G# Minor": "1A",
    "G# Min": "1A",
    "Ebm": "2A",
    "Eb Minor": "2A",
    "Eb Min": "2A",
    "D#m": "2A",
    "D# Minor": "2A",
    "D# Min": "2A",
    "Bbm": "3A",
    "Bb Minor": "3A",
    "Bb Min": "3A",
    "A#m": "3A",
    "A# Minor": "3A",
    "A# Min": "3A",
    "Fm": "4A",
    "F Minor": "4A",
    "F Min": "4A",
    "Cm": "5A",
    "C Minor": "5A",
    "C Min": "5A",
    "Gm": "6A",
    "G Minor": "6A",
    "G Min": "6A",
    "Dm": "7A",
    "D Minor": "7A",
    "D Min": "7A",
    "Am": "8A",
    "A Minor": "8A",
    "A Min": "8A",
    "Em": "9A",
    "E Minor": "9A",
    "E Min": "9A",
    "Bm": "10A",
    "B Minor": "10A",
    "B Min": "10A",
    "F#m": "11A",
    "F# Minor": "11A",
    "F# Min": "11A",
    "Gbm": "11A",
    "Gb Minor": "11A",
    "Gb Min": "11A",
    "Dbm": "12A",
    "Db Minor": "12A",
    "Db Min": "12A",
    "C#m": "12A",
    "C# Minor": "12A",
    "C# Min": "12A",
}


@dataclass
class PlaylistInfo:
    """Basic info about a Rekordbox playlist."""

    id: str
    name: str
    path: str
    count: int


class RekordboxLoader:
    """Handles interaction with Rekordbox 6 database."""

    def __init__(self):
        if not HAS_PYREKORDBOX:
            raise ImportError(
                "pyrekordbox is not installed. Install with 'pip install pyrekordbox'"
            )
        try:
            self.db = Rekordbox6Database()
        except Exception as e:
            # Often fails if configuration file is missing or db locked
            raise RuntimeError(f"Failed to initialize Rekordbox database: {e}") from e

    def _convert_key(self, key_str: str | None) -> str:
        """Convert Rekordbox tonality to Camelot key."""
        if not key_str:
            return ""

        # Already in Camelot? (e.g. "8A", "12B")
        if key_str[0].isdigit() and key_str[-1] in ("A", "B"):
            return key_str

        return KEY_MAPPING.get(key_str, key_str)

    def _normalize_energy(self, rating: int) -> int:
        """Normalize Rekordbox rating (0-255 or 0-5) to 1-5 energy scale."""
        if rating <= 0:
            return 1  # Default for unrated

        if rating <= 5:
            return rating

        # Handle 0-255 scale (51 per star)
        # 255=5, 204=4, 153=3, 102=2, 51=1
        normalized = round(rating / 51)
        return max(1, min(5, normalized))

    def list_playlists(self) -> list[PlaylistInfo]:
        """List all available playlists in the database."""
        playlists = []

        # pyrekordbox get_playlist() returns a list of playlist objects
        # The structure is hierarchical, but we'll try to flatten or just show top/relevant ones
        # For simplicity, let's just get the flat list if possible or walk the tree
        # Using the standard iterator which usually walks everything

        for pl in self.db.get_playlist():
            # Filter out folders or root
            if pl.Name == "ROOT":
                continue

            # Calculate full path or just use name
            # Assuming flat list for now or just top level
            try:
                count = len(pl.Songs) if hasattr(pl, "Songs") else 0
                playlists.append(
                    PlaylistInfo(
                        id=str(pl.ID),
                        name=pl.Name,
                        path=pl.Name,  # Ideally we'd construct the path
                        count=count,
                    )
                )
            except Exception as e:
                logger.warning(f"Error reading playlist {pl.Name}: {e}")

        return playlists

    def get_tracks(self, playlist_name: str) -> list[Track]:
        """Get tracks from a specific playlist by name."""
        target_pl = None
        for pl in self.db.get_playlist():
            if pl.Name == playlist_name:
                target_pl = pl
                break

        if not target_pl:
            raise ValueError(f"Playlist '{playlist_name}' not found")

        tracks = []
        for song in target_pl.Songs:
            content = song.Content

            if not content:
                continue

            try:
                # Rekordbox specific fields
                title = content.Title or "Unknown"
                artist = content.Artist.Name if content.Artist else "Unknown"
                track_id = f"{artist} - {title}"

                # Try to get path - usually FolderPath in DB
                path = getattr(content, "FolderPath", None)
                rb_id = getattr(content, "ID", None)

                bpm_raw = content.BPM or 0
                bpm_val = bpm_raw / 100.0 if bpm_raw > 200 else float(bpm_raw)

                key_raw = getattr(content, "KeyName", None)
                if not key_raw:
                    key_raw = getattr(content, "Tonality", None)

                key = self._convert_key(key_raw)

                if not key or bpm_val <= 0:
                    logger.warning(
                        f"Skipping track {track_id}: Missing Key ({key_raw}) or BPM ({bpm_val})"
                    )
                    continue

                tracks.append(
                    Track(
                        id=track_id,
                        key=key,
                        bpm=bpm_val,
                        energy=self._normalize_energy(int(content.Rating or 0)),
                        duration=float(content.Length or 0),
                        path=path,
                        title=title,
                        artist=artist,
                        rekordbox_id=rb_id,
                    )
                )
            except Exception as e:
                logger.warning(f"Error parsing track in playlist: {e}")
                continue

        return tracks

    def write_playlist_to_db(self, result: PlaylistResult, name: str):
        """Write the optimized playlist directly to the Rekordbox database."""
        if not self.db:
            raise RuntimeError("Database not initialized")

        logger.info(f"Creating playlist '{name}' in Rekordbox database...")

        # 1. Create playlist
        try:
            # We create in root for simplicity
            # Note: create_playlist returns the new playlist object or ID
            new_pl = self.db.create_playlist(name)

            # If it returns ID/object, we use it.
            # Pyrekordbox documentation suggests it returns the object.
        except Exception as e:
            raise RuntimeError(f"Failed to create playlist '{name}': {e}") from e

        # 2. Add tracks
        success_count = 0
        for track in result.playlist:
            if not track.rekordbox_id:
                logger.warning(f"Track '{track.id}' has no Rekordbox ID, skipping add to DB.")
                continue

            try:
                # We need to find the content object again or use ID if supported
                # get_content lookup might be needed if add_to_playlist expects object
                content = self.db.get_content(ID=track.rekordbox_id)
                if content:
                    self.db.add_to_playlist(new_pl, content)
                    success_count += 1
                else:
                    logger.warning(f"Content ID {track.rekordbox_id} not found in DB")
            except Exception as e:
                logger.warning(f"Failed to add track {track.id}: {e}")

        # 3. Commit
        try:
            self.db.commit()
            logger.info(f"Successfully created playlist '{name}' with {success_count} tracks.")
        except Exception as e:
            raise RuntimeError(f"Failed to commit changes to database: {e}") from e


def write_rekordbox_xml(result: PlaylistResult, source_playlist_name: str, output_path: Path):
    """
    Write optimization result to a Rekordbox-compatible XML file.

    The output filename is based on the source playlist name + timestamp,
    unless output_path is explicitly provided with a full path.
    """

    # Create root
    root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
    ET.SubElement(root, "PRODUCT", Name="rekordbox", Version="6.0.0", Company="AlphaTheta")

    # COLLECTION
    collection = ET.SubElement(root, "COLLECTION", Entries=str(len(result.playlist)))

    track_id_map = {}

    for i, track in enumerate(result.playlist, 1):
        # We need a numeric TrackID for internal reference in XML
        # We'll just use the index for simplicity
        track_ref_id = str(i)
        track_id_map[track.id] = track_ref_id

        # Prepare location - Rekordbox expects file:// URL format or absolute path
        # Usually it is file://localhost/path...
        # We will try to preserve what we got or standard format
        location = track.path if track.path else ""
        if location and not location.startswith("file://"):
            # Ensure it's properly quoted for URL
            # basic encoding
            path_part = quote(location)
            location = f"file://localhost{path_part}"

        track_elem = ET.SubElement(
            collection,
            "TRACK",
            TrackID=track_ref_id,
            Name=track.title or "Unknown",
            Artist=track.artist or "Unknown",
            Kind="Music",
            TotalTime=str(int(track.duration)),
            AverageBpm=str(track.bpm),
            Tonality=track.key,
            Rating=str(track.energy),
        )
        if location:
            track_elem.set("Location", location)

    # PLAYLISTS
    playlists_node = ET.SubElement(root, "PLAYLISTS")
    root_node = ET.SubElement(playlists_node, "NODE", Type="0", Name="ROOT", Count="1")

    # Generate playlist name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    playlist_name = f"{source_playlist_name}_{timestamp}"

    playlist_node = ET.SubElement(
        root_node,
        "NODE",
        Name=playlist_name,
        Type="1",
        KeyType="0",
        Entries=str(len(result.playlist)),
    )

    for track in result.playlist:
        ref_id = track_id_map.get(track.id)
        if ref_id:
            ET.SubElement(playlist_node, "TRACK", Key=ref_id)

    # Write to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)

    try:
        with open(output_path, "wb") as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding="utf-8", xml_declaration=False)
        logger.info(f"Rekordbox XML exported to {output_path}")
    except Exception as e:
        logger.error(f"Failed to write Rekordbox XML: {e}")
        raise
