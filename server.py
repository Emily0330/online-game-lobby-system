import socket
import time

# linux_server = input("Which linux server are you on? (1, 2, 3, or 4): ")
# MY_IP = f"140.113.235.15{linux_server}"
MY_IP = f"140.113.235.152"
MY_PORT = 40169

user_dict = {} # username:[pwd,state,ip,port]
room_dict = {} # room_idx:['private','roomhost','waiting/ingame/dissolve', 'game1/game2', 'another person']
game_dict = {} # game_name:[developer, introduction]
room_idx = 0

def build_connection(my_ip, my_port, player_ip, player_port):
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    skt.bind((my_ip,my_port))
    skt.connect((player_ip,player_port))
    connected = True
    return skt, connected

server_start = False
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind((MY_IP, MY_PORT)) # do i have to bind?
    s.listen(5) # the max size of waiting queue of connection is 5
    server_start = True
    print("The game server starts, waiting for players to connect.")
except Exception as e:
    print(e)
    print("Some error occurred when starting the server.")

if server_start:
    
    with open("players.txt","r", encoding = "utf-8") as f: # can read or append, create if not exists
        line = f.readline() # ignore the first rows, which are the keys
        # print(f'line: {line}')
        line = f.readline().rstrip('\n')
        while line and len(line) > 0:
            player = []
            player = line.split(',')
            user_dict[player[0]] = [player[1], 'log_out', 'init_ip', -1] # initialize
            line = f.readline().rstrip('\n')
        
        print("Existing users:") # test
        # print(len(user_dict))
        for key,value in user_dict.items(): # test
            print(f"user: {key}, pwd: {value[0]}")
    with open("games.txt","r", encoding = "utf-8") as f: # can read or append, create if not exists
        line = f.readline() # ignore the first rows, which are the keys
        # print(f'line: {line}')
        line = f.readline().rstrip('\n')
        while line and len(line) > 0:
            game_list = line.split(',')
            game_dict[game_list[0]] = [game_list[1], game_list[2]] # initialize
            line = f.readline().rstrip('\n')
        
        print("Existing games:") # test
        for key,value in game_dict.items(): # test
            print(f"name: {key}, developer: {value[0]}, introduction: {value[1]}")
    while True:
        new_skt, addr = s.accept()
        print(f"Connected with client at ip {addr[0]}, port {addr[1]}")
        first_time = True
        username = 'not_yet_set'
        name_exist = True # initialized here due to scope
        while True:
            action = new_skt.recv(1024).decode('ascii')

            print(f"action: {action}") # test
            if action == 'R' or action == 'LI':
                if first_time:
                    prompt1 = "Please enter your username: "
                    new_skt.send(prompt1.encode())
                    first_time = False
                
                username = new_skt.recv(1024).decode('ascii')
                name_exist = (username in user_dict)

                if (action == 'LI' and name_exist) or (action == 'R' and not name_exist):
                    new_skt.send(b"Please enter your password: ")
                    pwd = new_skt.recv(1024).decode('ascii')
                    
                    if action == 'R':
                        user_dict[username] = [pwd, 'log_out', 'init_ip', -1] # add username & pwd to dict
                        first_time = True

                        with open('players.txt','a') as f:
                            f.write(f"{username},{pwd}\n")

                        new_skt.send(b"Registration succeeds! Please type LI to login: ")
                        # break
                    else:
                        if pwd == user_dict[username][0]:
                            logged_in = "Login succeeds!" 
                            new_skt.send(logged_in.encode())
                            user_dict[username][1] = 'idle'
                            user_dict[username][2] = addr[0] # player ip
                            user_dict[username][3] = addr[1] # player port
                            # display online status
                            table_str = "\nroom_idx | private/public | roomhost | status    | game\n"
                            table_str += "----------------------------------------------------\n"
                            for idx, values in room_dict.items():
                                if values[2] != 'dissolve':
                                    table_str += f"{idx:<8} | {values[0]:<14} | {values[1]:<8} | {values[2]:<9} | {values[3]}\n"
                            
                            new_skt.send(table_str.encode())

                            player_str = "\n     username     |  state  \n"
                            player_str += "-----------------------------\n"
                            for idx, values in user_dict.items():
                                if values[1] != "log_out":
                                    player_str += f"{idx:<17} | {values[1]}\n"
                            new_skt.send(player_str.encode())
                            break
                        else: # wrong pwd
                            new_skt.send(b"Incorrect password.")  
                else: 
                    if action == 'R': # invalid username
                        new_skt.send(b"Username already exists. Please enter another username: ")
                    else: # not yet registered
                        new_skt.send(b"You are not registered. Please type R to register: ")
            elif action == 'C':

                # send available games
                game_str = "  Game Name  |  Developer  |  Introduction  \n"
                game_str += "---------------------------------------------\n"
                for key,value in game_dict.items():
                    game_str += f"{key:<13}|{value[0]:<13}|{value[1]:<16}\n"
                new_skt.send(game_str.encode())

                reply = new_skt.recv(1024).decode('ascii') # pub_or_pri + "," + game + "," + my_username
                pub_or_pri,game_type,username = reply.split(',')

                # old code
                # new_skt.send(b"Do you want a public room (1) or a private one (2): ")
                # reply = new_skt.recv(1024).decode('ascii')
                pub_or_pri = 'public' if pub_or_pri == '1' else 'private'
                
                room_dict[room_idx] = [pub_or_pri, username, 'waiting', game_type]
                user_dict[username][1] = 'in_room'
                print(f"change user {username}'s state to in_room.") # test

                msg = game_dict[game_type][0] + "," + game_dict[game_type][1]
                new_skt.send(msg.encode())

                _ = new_skt.recv(1024).decode('ascii')

                room_created_msg = f"Room created successfuly! The room id is {room_idx}."
                room_idx += 1
                new_skt.send(room_created_msg.encode())

                break
            elif action == 'J':
                
                co = 0
                public_rooms = "\nroom_idx | private/public | roomhost | status    | game\n"
                public_rooms += "----------------------------------------------------\n"
                for idx, values in room_dict.items():
                    if values[2] == 'waiting' and values[0] == 'public':
                        co += 1
                        public_rooms += f"{idx:<8} | {values[0]:<14} | {values[1]:<8} | {values[2]:<9} | {values[3]}\n"
                if co == 0:
                    new_skt.send(b"No public game rooms available")
                    print("No public rooms available")
                    new_skt.close()
                    break
                else: # there's room available
                    print(public_rooms) # test
                    public_rooms += "\nWhich public room do you want to join? Please enter room id: "
                    new_skt.send(public_rooms.encode())
                    valid_room = False
                    while not valid_room:
                        public_room_id = int(new_skt.recv(1024).decode('ascii'))
                        if room_dict[public_room_id][2] != 'waiting':
                            
                            room_full_err = 'The room is full. Please choose another public waiting room. \n'
                            print("tell player to choose another room.") # test
                            new_skt.send(room_full_err.encode())
                        else:
                            valid_room = True
                            print("Valid room found!")
                            
                    # the room is valid to join
                    public_room_game_type = room_dict[public_room_id][3]
                    new_skt.send(public_room_game_type.encode())
                    username = new_skt.recv(1024).decode('ascii')
                    new_skt.close()
                    connected = False
                    time.sleep(1)

                    try:
                        room_host_ip = user_dict[room_dict[public_room_id][1]][2]
                        room_host_port = user_dict[room_dict[public_room_id][1]][3]
                        print(f"room_host ip: {room_host_ip}, port: {room_host_port}") # test
                        new_skt, connected = build_connection(MY_IP,40171,room_host_ip,room_host_port + 1) # room host port or + 1?
                    except Exception as e:
                        print(e)
                        print("Fail to reconnect to the public room host.")
                    
                    if connected:
                        new_skt.send(b"Another player is found!")
                        new_skt.close()

                        try:
                            # give room addr to person to join
                            print(f"player 2 ip: {user_dict[username][2]}, port: {user_dict[username][3]}") # test
                            new_skt, connected = build_connection(MY_IP,40173,user_dict[username][2],user_dict[username][3])
                            if connected:
                                print("will tell the person to join room information!")
                                
                                room_dict[public_room_id][2] = 'in_game'
                                room_dict[public_room_id].append(username)

                                game_ip = room_host_ip
                                game_port = str(room_host_port + 1)
                                
                                new_skt.send(game_ip.encode())
                                _ = new_skt.recv(1024).decode('ascii') # discard the return msg
                                new_skt.send(game_port.encode())
                                _ = new_skt.recv(1024).decode('ascii') # game port received success
                                new_skt.send(public_room_game_type.encode())
                                _ = new_skt.recv(1024).decode('ascii') # game type received success
                                msg = game_dict[public_room_game_type][0] + "," + game_dict[public_room_game_type][1]
                                new_skt.send(msg.encode())

                                user_dict[room_dict[public_room_id][1]][1] = 'in_game'
                                user_dict[username][1] = 'in_game'

                                new_skt.close()
                                connected = False
                                time.sleep(3) # modified
                                break
                        except Exception as e:
                            print(e)
                            print("Fail to connect to player 2 (want to convey room host address)")
    
                    break
            elif action == 'I': # invite
                cnt_idle = 0
                player_str = "\n     username     |  state  \n"
                player_str += "-----------------------------\n"
                for idx, values in user_dict.items():
                    if values[1] == "idle":
                        cnt_idle += 1
                        player_str += f"{idx:<17} | {values[1]}\n"
                print(user_dict) # test
                if cnt_idle == 0:
                    new_skt.send(b"No available players.")
                    break
                new_skt.send(player_str.encode())
                # person_to_invite = new_skt.recv(1024).decode('ascii')
                while True:
                    person_to_invite = new_skt.recv(1024).decode('ascii')
                    # print(person_to_invite)
                    if person_to_invite in user_dict:
                        break
                    else:
                        new_skt.send(b"Player not found.")
                
                new_skt.send(b"okay, give me username.")
                inviter_addr = addr
                inviter_name = new_skt.recv(1024).decode('ascii')
                
                new_skt.close()
                connected = False
                time.sleep(1) # wait for new_skt being properly closed
                # connect to the player to invite
                try:
                    new_skt, connected = build_connection(MY_IP,40170,user_dict[person_to_invite][2],user_dict[person_to_invite][3]+2)
                    print("Successfully connect with the person to invite. Ready to send the invitation.")
                    print(f"person_to_invite ip: {user_dict[person_to_invite][2]}, port: {user_dict[person_to_invite][3] + 2}")
                except Exception as e:
                    print(e)
                    print("Server fails to connect with the person you want to invite. Please try again later.")

                if connected:
                    # send inviter's ip and port
                    invitation = f"{inviter_name} wants to invite you to join the game room. Accept the invitation? (Y/N): "
                    new_skt.send(invitation.encode())
                    join_or_not = new_skt.recv(1024).decode('ascii')
                    
                    new_skt.close()
                    connected = False
                    time.sleep(3)

                    try:
                        print(inviter_addr)
                        new_skt, connected = build_connection(MY_IP,40171,inviter_addr[0],inviter_addr[1]+1)
                    except:
                        print("Fail to reconnect to the inviter.")

                    if connected:
                        new_skt.send(join_or_not.encode())
                        new_skt.close()
                        connected = False
                        time.sleep(1)
                        if join_or_not == 'N':
                            break
                        else: # the invitation is accepted
                            try:
                                new_skt, connected = build_connection(MY_IP,40170,user_dict[person_to_invite][2],user_dict[person_to_invite][3]+2)
                            except Exception as e:
                                print(e)
                                print("Fail to reconnect to the person to invite, 2nd phase.")

                            if connected:
                                print("will tell the person to invite room information!")
                                game_type = 'no_game'
                                for idx, values in room_dict.items(): # update the room status
                                    if values[1] == inviter_name and values[2] != 'dissolve':
                                        room_dict[idx][2] = 'in_game' # change the room's state
                                        room_dict[idx].append(person_to_invite) # add another player to the end of the room list of the room
                                        game_type = room_dict[idx][3]
                                        break
                                if game_type == 'no_game':
                                    print("game type not exist, default game1")
                                game_type = 'game1' if game_type == 'no_game' else game_type
                                game_ip = inviter_addr[0]
                                game_port = str(inviter_addr[1] + 1)
                                
                                new_skt.send(game_ip.encode())
                                _ = new_skt.recv(1024).decode('ascii') # discard the return msg
                                new_skt.send(game_port.encode())
                                _ = new_skt.recv(1024).decode('ascii') # game port received success
                                new_skt.send(game_type.encode())
                                _ = new_skt.recv(1024).decode('ascii') # game type received success
                                print(_) # test: game type received
                                game_info = game_dict[game_type][0] + "," + game_dict[game_type][1]
                                new_skt.send(game_info.encode())

                                user_dict[inviter_name][1] = 'in_game'
                                user_dict[person_to_invite][1] = 'in_game'

                                new_skt.close()
                                connected = False
                                time.sleep(3) # modified
                                break
            elif action == 'NE':
                new_skt.send(b"give_me_username")
                username = new_skt.recv(1024).decode('ascii')
                for idx, values in room_dict.items():
                    if values[1] == username and values[2] != 'dissolve':
                        user_dict[username][1] = 'idle'
                        user_dict[values[4]][1] = 'idle'
                        room_dict[idx][2] = 'dissolve' # dissolve the room
                        print(f"Dissolve the room id {idx}")
                        break
                break
            elif action == 'LO':
                new_skt.send(b"give_me_username")
                username = new_skt.recv(1024).decode('ascii')
                user_dict[username][1] = 'log_out'
                new_skt.send(b"Log out successfully!")
                break
            elif action == 'U': # upload (or Update) game file
                new_skt.send(b"file uploaded")
                msg = new_skt.recv(1024).decode('ascii') # msg = username + " " + filename + " " + introduction
                msg_list = msg.split(',')
                developer = msg_list[0]
                game_name = msg_list[1]
                introduction = msg_list[2]
                game_dict[game_name] = [developer,introduction]
                
                # with open('games.txt','a') as f:
                #     f.write(f"{game_name},{developer},{introduction}\n")
                with open("games.txt", "w") as f:
                    f.write("GameName,Developer,Introduction\n")
                    for game_name, details in game_dict.items():
                        developer, introduction = details
                        f.write(f"{game_name},{developer},{introduction}\n")
                
                print(f"Game {game_name} uploaded successfully.\n")
                print(game_dict) # test
                break
            elif action == 'D': # get downloaded file information
                new_skt.send(b"Request received.")
                game = new_skt.recv(1024).decode('ascii')
                msg = game + "," + game_dict[game][0] + "," + game_dict[game][1]
                new_skt.send(msg.encode())
                break
            # elif action == "D_PRI":
            #     # try:
            #     #     skt, connected = build_connection()
            elif action == "LG":
                game_str = "  Game Name  |  Developer  |  Introduction  \n"
                game_str += "---------------------------------------------\n"
                for key,value in game_dict.items():
                    game_str += f"{key:<13}|{value[0]:<13}|{value[1]:<16}\n"
                    # print("game_str: ", game_str) # test
                
                new_skt.send(game_str.encode())
                break
            elif action == "GD":
                new_skt.send(b"received action GD")
                username = new_skt.recv(1024).decode('ascii')

                if user_dict[username][1] == 'idle':
                    user_dict[username][1] = 'in_GD_mode'
                elif user_dict[username][1] == 'in_GD_mode':
                    user_dict[username][1] = 'idle' # when user in game development mode wants to return to lobby
                new_skt.send(b"successfully updates your state in server.")
                break
            else:
                print(f"{action} action is not yet implemented./The client disconnects.")
                break
        
        new_skt.close()
