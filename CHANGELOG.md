# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.25.0] - 2024-12-26
### Added
- The Fleet widget displays the number of ships `[alive/total]` in its header.
- Computer player doesn't shoot cells, adjacent to a destroyed ship when `No adjacent 
ships` rule is enabled.
- Added support for Python 3.13.
### Changed
- Updated Textual, sentry-sdk, pyjwt.

## [0.24.1] - 2024-08-30
### Fixed
- Fix the excessive rounding of the win/loss ratio and accuracy.

## [0.24.0] - 2024-08-27
Finally, the alpha release of Battleship TUI is here. Hooray!

It took more than a year for a project to reach its current state. Most of the features 
are there, they work (maybe not flawlessly, but they do), you can play both singleplayer 
and multiplayer, track your statistics, and even have a little fun (if you dare to).

I feel just a bit tired, but also happy. I don't know what comes next, but the milestone 
has been reached.
