# online-game-lobby-system
This project is based on the final project of the course Introduction of Network Programming at NYCU. I refined the project and wrote a `Makefile` and a README for it.

The game system is composed of 3 sub-systems:  
1. Room system
2. Invitation system
3. Game development system  
## Table of Contents
* [Files](#files)
* [Background Setting](#background-setting)
* [Room System](#room-system)
* [Invitation System](#invitation-system)
* [Game Development System](#game-development-system)
* [Error Handling](#error-handing)

## Files
* `client.py`: Player(client) in the game system
    * `client1.py`, `client2.py`, ... are just the same code for demo use.
* `server.py`: Lobby server of the system
* The following files are used to keep the information so that the data won't disappeared after restarting the lobby server.
    * `player.txt`: keep track of registered players
    * `games.txt`: keep track of the games that have been uploaded to the lobby server
* `clientX_game`, `clientX_download` folder: for demo use
* `Makefile`
## Background Setting
* The players (clients) have the following 5 states:
    * `idle`: The player is in the lobby (logged in)
    * `in_room`: The player is in a room (either the room host or the invited player)
    * `in_game`: The player is playing games
    * `in_game_development`: The player is in the game development mode
    * `logged_out`: The player has logged out
* The lobby server is responsible for managing all the clients' states and helping communication among players.
## Room system
* All implementations use the **TCP** protocol
* Any `idle` player can create a room (room host), which falls into the following 2 categories:
    * public room: any other idle player can join the room
    * private room: the room host can invite any idle player to join the room
* When creating the room, the room host can choose which game he/she wants to play.
* When the room is full, the chosen game is automatically downloaded to the players' `download_folder` and starts.
* After the game ended, the room will dissolve (解散), the two players' states become `idle`.
* Note: 
    * A room can accommodate at most two players.
    * After joining the room, the player's state becomes `in_room`

## Game Development System
* Any idle player can enter game development mode (the state will become `in_game_development`).
* In game development mode, a player can
    * Upload/Update the game they develop (Python file) from their game folder to the lobby server
    * List the information of self-developed games
    * Return to lobby (become `idle` state)
* Note:
    * The uploaded file will be stored in lobby's game server, and 
    every player can play the game.
    * The game chosen by the room host will be downloaded to players' `clientX_download` folder, and
    the downloaded game is guaranteed to be the newest version of the game.

## Invitation System
* Private room hosts (to invite others)
    * Private room hosts can invite any idle player to their rooms.
        * If the invitation is rejected, the room host can send invitation to other idle player.
        * Otherwise, the room becomes full, and the game starts automatically.
* Idle players (to be invited)
    * Each player (client) has an invitation listener, which listens to invitations from private room hosts (sent by the lobby)
    when the player is in idle state.
    * After receiving the invitation, the player can choose whether to accept the invitation.
        * If the player accepts the invitation, he will enter the private room, and the state is modified to `in_room`.
        * Otherwise, the player will return to the original state (idle).

# Error Handing
* This is the part that makes the code really long, I will list a few points.
    * When playing the game, one of the player (client) shuts down, the other player should be informed and return to lobby.
    * If the lobby server shuts down, all the players should be informed and return to the login interface.