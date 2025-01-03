import socket
import threading
import time
import paramiko
# from game1 import play_game1_client, play_game1_server
# from game2 import play_game2_client, play_game2_server
# ===== for dynamically import =====
import importlib.util
import os
import sys

client_num = 2

MY_IP = '0.0.0.0'
MY_PORT = int(input("Please enter which port you want to set the server on: "))

# server_ip = input("Please enter the game server IP you want to connect to: ")
# server_port = int(input("Please enter the game server port: "))
server_ip = '140.113.235.152'
server_port = 40169

connected = False
loggedin = False
start_game = False
joining_public_room = False
join_room_game_type = 'not_yet_set' # remember to reset these value
my_state = 'idle'
my_username = 'not_yet_set_name' # remember to reset once log out
my_pwd = 'not_yet_set_pwd' # remember to reset once log out
my_room = ['no_room', MY_IP, MY_PORT, 'no_game'] # 'public/private/no_room', room_ip, room_port, game1
invitation_list = [] # store [invitor, room id] 
game_dict = {} # game_name:[developer, introduction]. This is games already downloaded from server
my_game_set = set()
download_folder = f"/u/cs/111/111550131/HW3/client{client_num}_download"
# username = "not_yet_set"


lock = threading.Lock()
lock_reply = threading.Lock()
invitation_listener_stop = False
invitation_received = False
global_reply = 'not_yet_set'

def load_module_from_download_folder(module_name, folder_path):
    """
    動態載入模組
    :param module_name: 模組名稱（不含副檔名 .py）
    :param folder_path: 模組所在的資料夾路徑
    :return: 載入的模組物件
    """
    module_path = os.path.join(folder_path, f"{module_name}.py")
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"模組 {module_name} 尚未下載到 {folder_path}。")

    # 動態載入模組
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # 將模組添加到 sys.modules 中
    spec.loader.exec_module(module)  # 執行模組內容
    return module
def play_game(client_or_server, game_type, skt):
    global download_folder
    try:
        # module_name = "game1"
        loaded_game = load_module_from_download_folder(game_type, download_folder)

        # 動態呼叫函數
        if client_or_server == 'client':
            client = getattr(loaded_game, "client", None)
            if client: # and play_game1_server
                client(skt)
            else:
                print("No client module in this game.")

        else:
            server = getattr(loaded_game, "server", None)
            if server: # and play_game1_server
                server(skt)
            else:
                print("No server module in this game.")
  
    except FileNotFoundError as e:
        print(e)

def upload_game_to_server(filename): # input filename does not have .py extension # if succeed, return true
    # 檔案路徑
    global server_ip, server_port, client_num
    username = "cychang0330"
    password = "hebe0330"
    server_dir = "/u/cs/111/111550131/HW3/server_game/"
    client_dir = f"/u/cs/111/111550131/HW3/client{client_num}_game/"
    local_file = f"{client_dir}{filename}.py"  # 客戶端檔案
    remote_file = f"{server_dir}{filename}.py"  # 伺服器檔案
    local_file_download = f"/u/cs/111/111550131/HW3/client{client_num}_download/{filename}.py"
    try:
        # 建立 Transport 連線
        transport = paramiko.Transport((server_ip, 22))
        transport.connect(username=username, password=password)

        # 建立 SFTP 連線
        sftp = paramiko.SFTPClient.from_transport(transport)

        # 上傳檔案
        sftp.put(local_file, remote_file)
        print(f"Successfully upload the game file to server: {remote_file}")

        # 從伺服器下載檔案
        sftp.get(remote_file, local_file_download)
        print(f"Also download to your download folder: {local_file_download}")
        
        return True

    except Exception as e:
        print(f"操作失敗: {e}")
        return False

    finally:
        # 關閉連線
        if sftp:
            sftp.close()
        if transport:
            transport.close()

def download_game_from_server(filename): # input filename does not have .py extension
    # 檔案路徑
    global server_ip, server_port, client_num
    username = "cychang0330"
    password = "hebe0330"
    server_dir = "/u/cs/111/111550131/HW3/server_game/"
    client_dir = f"/u/cs/111/111550131/HW3/client{client_num}_download/"
    local_file = f"{client_dir}{filename}.py"  # 客戶端檔案
    remote_file = f"{server_dir}{filename}.py"  # 伺服器檔案

    try:
        # 建立 Transport 連線
        transport = paramiko.Transport((server_ip, 22))
        transport.connect(username=username, password=password)

        # 建立 SFTP 連線
        sftp = paramiko.SFTPClient.from_transport(transport)

        # 從伺服器下載檔案
        sftp.get(remote_file, local_file)
        print(f"Successfully download the game file from server: {local_file}")

    except Exception as e:
        print(f"操作失敗: {e}")

    finally:
        # 關閉連線
        if sftp:
            sftp.close()
        if transport:
            transport.close()

def build_connection(my_ip, my_port, player_ip, player_port):
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    skt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    skt.bind((my_ip,my_port))
    skt.connect((player_ip,player_port))
    connected = True
    return skt, connected

accept_invitation = False
def invitation_listener():
    global my_state, start_game, lock, invitation_listener_stop, invitation_received, lock_reply, accept_invitation, global_reply, game_dict, download_folder
    # print("The invitation listener starts!") # test
    tmp_server_start = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # accept_invitation = False
    game_ip = 'not_yet_known_ip' # declared here due to scope problem
    game_port = 'not_yet_known_port'
    try:
        s.bind((MY_IP, MY_PORT + 2)) # do i have to bind?
        s.listen(1) # allow game server to connect
        tmp_server_start = True
        # print("The temporary server starts, waiting for others to invite.")
    except:
        print("Some error occurred when starting the temporary server.")
    if tmp_server_start:
        while True:
            new_skt, addr = s.accept()
            # lock.acquire()
            if my_state == 'idle' : # and not invitation_listener_stop
                # lock.release()
                if not accept_invitation:
                    print(f"Connected with game server at ip {addr[0]}, port {addr[1]}")
                    invitation = new_skt.recv(1024).decode('ascii')
                    tmp_inv_list = invitation.split(' ')
                    invitation_list.append([tmp_inv_list[0],0]) # add host name, modify the room id! // TODO
                    print(invitation)
                    # print("acquiring lock by listener...") # test
                    lock.acquire()
                    # print("lock aquired!") # test
                    # print("acquiring lock_reply...") # test
                    lock_reply.acquire()
                    # print("lock_reply aquired!") # test
                    if global_reply == 'not_yet_set':
                        join_or_not = input()
                    elif global_reply == 'Y' or global_reply == 'N':
                        join_or_not = global_reply
                    else: # 'C' or 'LO' or 'J'
                        lock_reply.release()
                        # print("lock_reply released by listener.")
                        lock.release()
                        # print("lock released by listener.")
                        new_skt.close()
                        continue
                    lock_reply.release()
                    # print("lock_reply released by listener.")
                    
                    new_skt.send(join_or_not.encode())
                    if join_or_not == 'Y':
                        accept_invitation = True
                        print("Waiting for room information...")
                    else: # do not want to join the room
                        global_reply = 'not_yet_set' # newly added
                        print("Invitation rejected.")
                        lock.release()
                        # print("lock released by listener")
                        continue
                        # break
                    
                    new_skt.close()
                else: # has accepted the invitation or wanted to join public room  # get room information from game server
                    print(f"Connected with lobby server at ip {addr[0]}, port {addr[1]}")
                    game_ip = new_skt.recv(1024).decode('ascii')
                    new_skt.send(b"game ip received")
                    game_port = new_skt.recv(1024).decode('ascii')
                    print(f"game port: {game_port}") # test
                    game_port = int(game_port)
                    print(f"Receive game server's ip {game_ip} and port {game_port}, ready to connect...")
                    new_skt.send(b"game port received.")
                    join_room_game_type = new_skt.recv(1024).decode('ascii')
                    new_skt.send(b"game type received.")
                    msg = new_skt.recv(1024).decode('ascii')
                    developer, introduction = msg.split(',')
                    new_skt.close()
                    
                    if join_room_game_type not in game_dict:
                        print("You haven't downloaded the game file, ready to download...")
                        download_game_from_server(join_room_game_type)

                        game_dict[join_room_game_type] = [developer,introduction]
                        print("Game information successfully fetched from server.")
                    elif game_dict[join_room_game_type][0] != developer or game_dict[join_room_game_type][1] != introduction:
                        print("The game has been updated, ready to reload...")
                        download_game_from_server(join_room_game_type)

                        game_dict[join_room_game_type] = [developer,introduction]
                        print("Game information successfully fetched from server.")
                    
                    # print(f"join_room_game_type: {join_room_game_type}") # test
                    

                    start_game = True
                    my_state = 'in_game'
                    
                    if start_game:
                        try:
                            skt, connected = build_connection(MY_IP,MY_PORT+7,game_ip,game_port)
                        except Exception as e:
                            print("Failed to connect to game room server.")
                            print(e)
                        if connected:
                            global_reply = 'not_yet_set' # newly added
                            
                            play_game(client_or_server='client',game_type=join_room_game_type,skt=skt)
                            skt.close()

                    accept_invitation = False
                    lock.release()
                    # print("lock released by listener")
                    continue
            else:
                lock.release()
                new_skt.close()
        
# main function starts

invitation_listener_thread = threading.Thread(target = invitation_listener)
invitation_listener_thread.start()
lock_by_main = False
while True:
    # print(my_state)
    if not loggedin:
        action = input("(R) Register\n(LI) Login\nPlease choose an action: ")
        global_reply = 'not_yet_set'
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((MY_IP,MY_PORT))
            s.connect((server_ip,server_port))
            connected = True
        except Exception as e:
            print(e)
            print("Cannot connect to server.")
            time.sleep(3)

        if connected:
            
            first_time = True
            while True:
                s.send(action.encode())
                # print("sent action:",action) # test
                # print(first) # test
                if first_time:
                    username_prompt = s.recv(1024).decode('ascii')
                    my_username = input(username_prompt)
                    first_time = False
                s.send(my_username.encode())
                # print("sent usrname:",username) # test
                reply = s.recv(1024).decode('ascii')
                if "password" in reply: # username OK
                    pwd = input(reply)
                    s.send(pwd.encode())
                    # print("sent pwd:",pwd) # test
                    reply = s.recv(1024).decode('ascii')
                    
                    if reply == "Incorrect password.":
                        print(reply)
                        continue
                    elif reply == "Registration succeeds! Please type LI to login: ":
                        action = input(reply)
                        first_time = True
                        continue
                    else: # log in successfully?!
                        loggedin = True
                        # my_username = username
                        my_pwd = pwd
                        my_state = 'idle'
                        print(reply)
                        
                        online_status = s.recv(1024).decode('ascii')
                        print(online_status) # room list
                        online_status = s.recv(1024).decode('ascii')
                        print(online_status) # player list
                        break
                else:
                    if action == 'R': # registration fails
                        my_username = input(reply)
                    else: # login fails
                        action = input(reply)
            s.close()
            connected = False
    else: # logged in, show rooms or create room
        if my_state == 'idle':
            if lock_by_main:
                lock.release()
                lock_by_main = False
                # print("lock released by main!")
            # lock2.acquire()
            # print(f"global_reply: {global_reply}") # test
            if not joining_public_room and global_reply != 'Y' and global_reply != 'N':# and not invitation_received
                # print("acquiring lock by main...")
                lock.acquire()
                lock_by_main = True
                # print("lock aquired by main!") # test
                # print(f"my_state: {my_state}")
                # print("acquiring lock_reply by main...")
                lock_reply.acquire()
                # print("lock_reply acquired by main!")
                # print("global reply released by main")
                global_reply = 'not_yet_set'
                
                if my_state == 'in_game':
                    lock_reply.release()
                    # print("lock_reply released by main")
                    lock.release()
                    lock_by_main = False
                    # print("lock released by main")
                    
                    continue
                
                # print("prompt1: choose your action: ")
                # print("Do you want to create a room (C), join a public room (J), or log out (LO): ")
                print("========== In Game Lobby ==========\n(C) create a room\n(J) join a public room\n(LO) log out\n(IM) Go to Invitation Management\n(GD) Enter Game Development Mode\n(LG) List all games\nPlease choose an action: ", end="")
                # print(f"global reply: {global_reply}") # test
                if global_reply == 'not_yet_set':
                    global_reply = input()
                    action = global_reply
                elif global_reply == 'Y' or global_reply == 'N':
                    lock_reply.release()
                    # print("lock_reply released by main")
                    lock.release()
                    lock_by_main = False
                    # print("lock released by main")
                    continue
                else:
                    action = global_reply
                
                if global_reply == 'Y' or global_reply == 'N':
                    lock_reply.release()
                    # print("lock_reply released by main")
                    lock.release()
                    lock_by_main = False
                    # print("lock released by main")
                    continue
                # print(f"global reply: {global_reply}")
                
                lock_reply.release()
                # print("lock_reply released by main")

                invitation_listener_stop = True
            tmp_server_start = False
            if action == 'W' or joining_public_room: # waitng to join
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # test do i need
                accept_invitation = False
                game_ip = 'not_yet_known_ip' # declared here due to scope problem
                game_port = 'not_yet_known_port'
                try:
                    s.bind((MY_IP, MY_PORT)) # do i have to bind?
                    s.listen(1) # allow game server to connect
                    tmp_server_start = True
                    if joining_public_room:
                        print("The temporary server starts, waiting for room information.")
                    else:    
                        print("The temporary server starts, waiting for others to invite.")
                except:
                    print("Some error occurred when starting the temporary server.")
                
                if tmp_server_start:
                    while True:
                        new_skt, addr = s.accept()
                        if not accept_invitation and not joining_public_room:
                            print(f"Connected with lobby server at ip {addr[0]}, port {addr[1]}")
                            invitation = new_skt.recv(1024).decode('ascii')
                            join_or_not = input(invitation)
                            new_skt.send(join_or_not.encode())
                            if join_or_not == 'Y':
                                accept_invitation = True
                                print("Waiting for room information...")
                            else: # do not want to join the room
                                print("Invitation rejected.")
                                break
                            
                            new_skt.close()
                        else: # has accepted the invitation or wanted to join public room  # get room information from game server
                            print(f"Connected with lobby server at ip {addr[0]}, port {addr[1]}")
                            game_ip = new_skt.recv(1024).decode('ascii')
                            # okay = "game ip received"
                            new_skt.send(b"game ip received")
                            game_port = int(new_skt.recv(1024).decode('ascii'))
                            print(f"Receive game server's ip {game_ip} and port {game_port}, ready to connect...")
                            new_skt.send(b"game port received.")
                            join_room_game_type = new_skt.recv(1024).decode('ascii')
                            # print(f"join_room_game_type: {join_room_game_type}") # test
                            new_skt.send(b"game type received.")
                            msg = new_skt.recv(1024).decode('ascii')
                            developer,introduction = msg.split(',')

                            new_skt.close()
                            s.close()
                            connected = False # newly added
                            time.sleep(2)
                            
                            if join_room_game_type not in game_dict:
                                print("You haven't downloaded the game file, ready to download...")
                                download_game_from_server(join_room_game_type)

                                game_dict[join_room_game_type] = [developer,introduction]
                                print("Game information successfully fetched from server.")
                            elif game_dict[join_room_game_type][0] != developer or game_dict[join_room_game_type][1] != introduction:
                                print("The game has been updated, ready to reload...")
                                download_game_from_server(join_room_game_type)

                                game_dict[join_room_game_type] = [developer,introduction]
                                print("Game information successfully fetched from server.")

                            tmp_server_start = False
                            start_game = True
                            my_state = 'in_game'
                            break
                    if start_game:
                        try:
                            print(f"game room ip {game_ip}, port {game_port}")
                            skt, connected = build_connection(MY_IP,MY_PORT,game_ip,game_port)
                        except Exception as e:
                            print("Failed to connect to game room server.")
                            print(e)
                        if connected:
                            play_game(client_or_server='client',game_type=join_room_game_type,skt=skt)
                            # if join_room_game_type == 'game1':
                            #     play_game1_client(skt)
                            # else: # game2
                            #     play_game2_client(skt)
                            
                            skt.close()
                            time.sleep(3) # modified
                            my_state = 'idle'
                            join_room_game_type = 'not_yet_set' # reset join_room_game_type
                            start_game = False
                            joining_public_room = False
                            # break
            elif global_reply != 'Y' and global_reply != 'N':
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((MY_IP,MY_PORT))
                    s.connect((server_ip,server_port)) # to change an address
                    connected = True
                except:
                    print("Cannot connect to server. Please try again later.")
                
                joining_public_room = False # to control the socket close
                if connected:
                    # s.send(action.encode())
                    # print(f"action {action} sent to lobby.") # test
                    if action == 'C':
                        s.send(action.encode())
                        
                        pub_or_pri = input("Do you want a public room (1) or a private one (2): ")
                        game_str = s.recv(1024).decode('ascii')
                        game = input(game_str+"Please enter the game you want to play: ")
                        
                        msg = pub_or_pri + "," + game + "," + my_username
                        s.send(msg.encode())

                        msg = s.recv(1024).decode('ascii')
                        developer,introduction = msg.split(',')

                        s.send(b"got game information")

                        my_state = 'in_room' # change player state to in room
                        my_room[0] = 'public' if pub_or_pri == '1' else 'private'
 
                        reply = s.recv(1024).decode('ascii')# room creation success msg
                        
                        my_room[3] = game # 'game1' if game == '1' else 'game2'
                        # if game not in game_dict:
                        #     print("You haven't downloaded this game, ready to download...")
                        #     s.close()
                        #     time.sleep(1) # see whether to add
                        #     connected = False
                        #     download_game_from_server(game)
                        if game not in game_dict:
                            print("You haven't downloaded the game file, ready to download...")
                            download_game_from_server(game)

                            game_dict[game] = [developer,introduction]
                            print("Game information successfully fetched from server.")
                        elif game_dict[game][0] != developer or game_dict[game][1] != introduction:
                            print("The game has been updated, ready to reload...")
                            download_game_from_server(game)

                            game_dict[game] = [developer,introduction]
                            print("Game information successfully fetched from server.")
                        

                            # print(reply) # room creation success msg # 本來在if game not in game_dict:下
                            # continue # won't go to below to close s (already close)

                        print(reply) # room creation success msg

                    elif action == 'J': # action == 'J'
                        # print("I am going to join a public room!")
                        s.send(action.encode())
                        reply = s.recv(1024).decode('ascii')
                        if reply == 'No public game rooms available':
                            print(reply)
                            lock.release()
                            lock_by_main = False
                            continue
                        
                        while True:
                            public_room_id = input(reply) # ask which public room
                            s.send(public_room_id.encode())
                            reply = s.recv(1024).decode('ascii')
                            if 'room is full' in reply:
                                print(reply)
                            else:
                                break
                        # get room information
                        join_room_game_type = reply
                        # print(f"join_room_game_type: {join_room_game_type}") # test
                        joining_public_room = True
                        s.send(my_username.encode())

                    elif action == 'LO': # action == 'LO'
                        s.send(action.encode())
                        print("going to log out...")
                        loggedin = False
                        _ = s.recv(1024).decode('ascii') # asked for username
                        s.send(my_username.encode())
                        log_out_msg = s.recv(1024).decode('ascii')
                        print(log_out_msg)
                    
                    elif action == "IM":
                        my_state = 'in_invitaion_page'
                    elif action == "GD":
                        my_state = "game_development_page"
                        s.send(action.encode())
                        _ = s.recv(1024).decode('ascii') # ack
                        s.send(my_username.encode())
                        msg = s.recv(1024).decode('ascii')
                        print(msg) # successfully updates your state in server.

                    elif action == "LG": # list all the games
                        s.send(action.encode())
                        game_str = s.recv(1024).decode('ascii')
                        print(game_str)
                        
                s.close()
                connected = False
                time.sleep(1) # 不讓他太快下個iteration，讓socket好好關閉

        elif my_state == 'in_room':
            if my_room[0] == 'public':
                tmp_server_start = False
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((MY_IP,MY_PORT + 1))
                    s.listen(2) # allow game server to connect
                    tmp_server_start = True
                    print("The temporary server starts, waiting for response.")
                except Exception as e:
                    print(e)
                    print("Cannot connect to server. Please try again later.")
                
                if tmp_server_start:
                    # print("Waiting for another player to join...")
                    new_skt, addr = s.accept()
                    print(f"Connected with lobby at ip {addr[0]}, port {addr[1]}")
                    # start deliver ip & port of the room to lobby
                    player_found_msg = new_skt.recv(1024).decode('ascii')
                    print(player_found_msg, "Setting up the room server...")
                    
                    my_room[1] = MY_IP
                    my_room[2] = MY_PORT + 1
                    new_skt.close() # end the connection with the lobby server

                    time.sleep(2)
                    game_skt, player_addr = s.accept()
                    print(f"Waiting another player to connect at {my_room[1]},{my_room[2]}")
                    
                    print("Connected! Starting the game...")
                    my_state = 'in_game'
                    play_game(client_or_server='server',game_type=my_room[3],skt=game_skt)
                    game_skt.close()
                    # if my_room[3] == 'game1':
                    #     play_game1_server(game_skt)
                    #     game_skt.close()
                    #     # s will close below

                    # else: # game2
                    #     play_game2_server(game_skt)
                    #     game_skt.close()

            else: # private room
                action = input("Type I to see who you can invite, you can only invite idle player.")
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((MY_IP,MY_PORT))
                    s.connect((server_ip,server_port)) # to change an address
                    connected = True
                except:
                    print("Cannot connect to server. Please try again later.")
                
                if connected:
                    s.send(action.encode())
                    player_str = s.recv(1024).decode('ascii')
                    print(player_str)
                    if player_str == "No available players.":
                        s.close()
                        continue
                    
                    # person_to_invite = input("Please enter the idle player you want to invite: ")
                    while True:
                        person_to_invite = input("Please enter the idle player you want to invite: ")
                        s.send(person_to_invite.encode())
                        okay = s.recv(1024).decode('ascii') # receive okay msg
                        if 'okay' in okay:
                            break
                        else:
                            print(okay)
                    # s.recv(1024).decode('ascii') # receive okay msg
                    s.send(my_username.encode())
                    
                    s.close()
                    connected = False
                    time.sleep(3) # 讓s好好關閉

                    print("Waiting for response...")
                    tmp_server_start = False
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        print(MY_IP, MY_PORT)
                        s.bind((MY_IP, MY_PORT + 1)) # do i have to bind?
                        s.listen(1) # allow game server to connect
                        tmp_server_start = True
                        print("The temporary server starts, waiting for response.")
                    except:
                        print("Some error occurred when starting the temporary server.")
                    
                    if tmp_server_start: # waiting for server's connection
                        new_skt, addr = s.accept()
                        print(f"Connected with lobby at ip {addr[0]}, port {addr[1]}")
                        accepted = new_skt.recv(1024).decode('ascii')
                        if accepted == 'Y':
                            # go to set up the room server
                            print("going to set up the room server!")
                            my_room[1] = MY_IP
                            my_room[2] = MY_PORT + 1
                            new_skt.close() # end the connection with the lobby server
                            time.sleep(2)

                            print("Waiting another player to connect...")
                            game_skt, player_addr = s.accept() # wait for another client to connect
                            print("Connected! Starting the game...")
                            my_state = 'in_game'
                            play_game(client_or_server='server',game_type=my_room[3],skt=game_skt)
                            game_skt.close()
                            s.close()
                            # if my_room[3] == 'game1':
                            #     play_game1_server(game_skt)
                            #     game_skt.close()
                            #     # s will close below

                            # else: # game2
                            #     play_game2_server(game_skt)
                            #     game_skt.close()

                        else: # invitation rejected
                            print("Invitation rejected.")
                            new_skt.close()
                            s.close()
                            connected = False
                            tmp_server_start = False
                            time.sleep(5)
                        
            if action != 'I': # have closed the socket in I       
                s.close()
                connected = False
                time.sleep(5)
        elif my_state == 'in_game': # game server Notifies the End of the game (自己它的state，只有client自己有這個state，在lobby還是in_room)
            action = 'NE' #Notify End of the game to lobby server
            my_state = 'idle'
            my_room[0] = 'no_room' # the room dissolves
            lock_reply.acquire()
            global_reply = 'not_yet_set'
            lock_reply.release()
            try:
                skt, connected = build_connection(MY_IP, MY_PORT, server_ip, server_port)
            except Exception as e:
                print("Cannot connect to lobby server.")
                print(e)
            if connected:
                skt.send(action.encode())
                _ = skt.recv(1024).decode('ascii')
                skt.send(my_username.encode())
                
                skt.close()
                time.sleep(3) # change this from 5 to 3, see if it's ok
        elif my_state == 'in_invitaion_page':
            print("Invitation Management\n(1) List all the requests\n(2) Accept a request\n(3) Back to lobby")
            action_in_inv_page = input()
            if action_in_inv_page == '1':
                
                print("You received invitations from the following rooms.")
                invitation_str = "    invitor    |   room id    \n"
                invitation_str += "---------------|---------------\n"
                for x in invitation_list:
                    invitation_str += f"{x[0]:<14} |   {x[1]:<13}\n"
                print(invitation_str)

            elif action_in_inv_page == '2':
                print("Please enter the room id of the room you want to join:")
                room_id = int(input())
                # TODO: transfer to server
            
            elif action_in_inv_page == '3':
                print("Going back to lobby...")
                my_state = 'idle'
        elif my_state == 'game_development_page':
            print("======= Game Development Mode =======")
            action_game_page = input("(1) List your games\n(2) Upload game\n(3) Back to lobby\nPlease choose an action: ")
            if action_game_page == '1':
                game_str = "  Game Name  |  Developer  |  Introduction  \n"
                game_str += "---------------------------------------------\n"
                for x in my_game_set:
                    game_str += f"{x:<13}|{game_dict[x][0]:<13}|{game_dict[x][1]:<16}\n"
                
                print(game_str)
            elif action_game_page == '2':
                filename = input("Enter your file name (ignore .py): ")
                introduction = input("Introduction of your game (please don't contain comma): ")
                upload_success = upload_game_to_server(filename=filename)
                if upload_success:
                    game_dict[filename] = [my_username,introduction] # add the uploaded games to dict
                    my_game_set.add(filename)
                    action = 'U'
                    try:
                        skt, connected = build_connection(MY_IP,MY_PORT,server_ip,server_port)
                        print("Connected with the lobby server, ready to upload file...")
                    except Exception as e:
                        print(e)
                    if connected:
                        skt.send(action.encode())
                        # print(f'action {action} sent successfully')
                        _ = skt.recv(1024).decode('ascii')
                        msg = my_username + "," + filename + "," + introduction
                        skt.send(msg.encode())
                        print("Game information sent successfully to server.")
                        skt.close()
                else:
                    print("Failed. Please make sure the game file is in your game folder and try again.")
            elif action_game_page == '3':
                my_state = 'idle'

                action = 'GD'
                try:
                    skt, connected = build_connection(MY_IP,MY_PORT,server_ip,server_port)
                    print("Connected with the lobby server, ready to return to lobby...")
                except Exception as e:
                    print(e)
                if connected:
                    skt.send(action.encode())
                    # print(f'action {action} sent successfully')
                    _ = skt.recv(1024).decode('ascii') # ack
                    # msg = my_username + "," + filename + "," + introduction
                    skt.send(my_username.encode())
                    msg = skt.recv(1024).decode('ascii')
                    print(msg) # successfully updates your state in server.
                    skt.close()

