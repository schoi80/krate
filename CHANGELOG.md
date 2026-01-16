# CHANGELOG

<!-- version list -->

## v1.3.0 (2026-01-16)

### Chores

- Renamed to djkr8
  ([`158a8a6`](https://github.com/schoi80/djkr8/commit/158a8a63fcc952865724fd7ca8030aee73e82a12))

### Features

- Rebranded to djkr8
  ([`4774480`](https://github.com/schoi80/djkr8/commit/47744803ccf3a06fbe9b1fc0c762cdac75ed8953))


## v1.2.0 (2026-01-16)

### Features

- Enforce energy range (1-5) and non-decreasing flow constraint
  ([`3346e7b`](https://github.com/schoi80/dj-playlist-optimizer/commit/3346e7b45166c098d10bbcf2b31dd5e1a62a9fe6))

- Make energy flow constraint togglable and update documentation
  ([`a1a9f5b`](https://github.com/schoi80/dj-playlist-optimizer/commit/a1a9f5b3b1d135f7a1f6af571ef10b94c7e87521))


## v1.1.0 (2026-01-16)

### Documentation

- Add new `AGENTS.md` files to `src` and `tests` directories and refactor the main `AGENTS.md` with
  updated project details.
  ([`87314cb`](https://github.com/schoi80/djkr8/commit/87314cb21da8ed4b9f14b0db08a062cd250cb09a))

### Features

- Add comprehensive test suite for Rekordbox integration, CLI, models, and optimizer features, and
  configure pytest-cov for coverage reporting.
  ([`2df81c5`](https://github.com/schoi80/djkr8/commit/2df81c58e9802cec72ffa1fa89eb4c1c3767f043))

- Add Rekordbox database integration for loading playlists and tracks via new CLI options.
  ([`0e3db17`](https://github.com/schoi80/djkr8/commit/0e3db17259deb0b8b8479dfb56037f289cf1e512))

- Introduce Rekordbox XML export and direct database integration for optimized playlists, including
  track metadata enrichment.
  ([`efcb547`](https://github.com/schoi80/djkr8/commit/efcb5474e8bd80917ddd0a6123bf8bd71f94b531))

### Testing

- Improve robustness of Rekordbox XML parsing assertions and adapt database mock to keyword
  arguments.
  ([`cfd9541`](https://github.com/schoi80/djkr8/commit/cfd95419b30da0e3717af6a03fc90470d8a64389))


## v1.0.0 (2026-01-16)

- Initial Release
