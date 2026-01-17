from djkr8 import PlaylistOptimizer, Track

print("Demo: Energy Flow Constraint (max +1 increase)\n")

tracks = [
    Track(id="low", key="8A", bpm=120, energy=1),
    Track(id="med", key="8A", bpm=120, energy=2),
    Track(id="high", key="8A", bpm=120, energy=4),
]

print("Tracks:")
for t in tracks:
    print(f"  {t.id}: energy={t.energy}")

print("\n--- With energy flow enforced (default) ---")
optimizer = PlaylistOptimizer(enforce_energy_flow=True)
result = optimizer.optimize(tracks)

print(f"Playlist length: {len(result.playlist)}")
for i, track in enumerate(result.playlist, 1):
    print(f"  {i}. {track.id} (energy={track.energy})")

print("\nNote: Cannot go from energy=1 to energy=4 directly (+3 exceeds max +1)")
print("Can only build: low(1) -> med(2)")

print("\n--- With energy flow disabled ---")
optimizer = PlaylistOptimizer(enforce_energy_flow=False)
result = optimizer.optimize(tracks)

print(f"Playlist length: {len(result.playlist)}")
for i, track in enumerate(result.playlist, 1):
    print(f"  {i}. {track.id} (energy={track.energy})")

print("\nNote: All tracks can be included when energy flow is disabled")
