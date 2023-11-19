# Battleship TUI
Battleship TUI is an implementation of the popular paper-and-pen Battleship game for 
your terminal. You can play against the AI or against a real player via Internet, 
customize game options and appearance, keep track of your achievements, and more.

## Features
* Singleplayer mode  
* Multiplayer mode (via Internet)
* Customizable game rules
* Game statistics

## Planned features
* Customizable UI 
* Ranking system

## Requirements
* A terminal (Windows PowerShell is fine too)
* Python 3.11 or higher

## Installation
The recommended way to install and update the game is via 
[pipx](https://pypa.github.io/pipx/) (especially if you don't know anything about 
virtual environments).

```shell
pipx install battleship-tui[client]
```

`battleship-tui` is merely a Python package and is distributed via PyPI. You can 
install it via `pip` too, but make sure it installs into a venv so that you're not 
messing with the system interpreter.

```shell
# Linux example.
python -m venv venv && source venv/bin/activate
pip install battleship-tui[client]
```

## Installation (server)
Here be dragons.

## Play
Once the game is installed you can use the `battleship` command to run it. This 
command will launch the user interface and present you with the main menu.

### Play via CLI
You can launch the game via CLI subcommands too, especially if you want to skip some 
in-game menus.

For example, if your favorite game mode is singleplayer, salvo variant, you can 
quickly get into battle by running `battleship play single --salvo`.

Run `battleship play --help` to discover available options.

## Multiplayer account
Here be dragons.
