def calculate_bulls_and_cows(secret, guess):
    """計算幾A幾B"""
    # bulls = sum(1 for s, g in zip(secret, guess) if s == g)
    bulls = 0
    for i in range(4):
        if secret[i] == guess[i]:
            bulls += 1
    cows = 0
    for i in range(4):
        if guess[i] in secret and guess[i] != secret[i]:
            cows += 1 
    return bulls, cows

def client(skt):
    # print("I am game2 client!")
    """客戶端邏輯"""
    client_secret = input("Please enter your secret number (4 different digits): ")
    client_attempts, server_attempts = 0, 0
    # msg = skt.recv(1024).decode('ascii')
    while True:
        # 客戶端的猜測
        client_guess = input("Please enter your guess (4 different digits): ")
        skt.send(client_guess.encode())
        client_attempts += 1

        # 接收伺服器的回應
        server_response = skt.recv(1024).decode()
        if len(server_response) == 0:
            print("Another player disconnects.")
            return
        print(f"server replies: {server_response}")

        if server_response == "win":
            print("You win!")
            break
        else:
            skt.send(b"your_turn")
            # 接收伺服器的猜測
            server_guess = skt.recv(1024).decode()
            if len(server_guess) == 0:
                print("Another player disconnects.")
                return
            print(f"Receive server guess: {server_guess}")

            # 計算伺服器的猜測結果
            server_attempts += 1
            bulls, cows = calculate_bulls_and_cows(client_secret, server_guess)
            response = f"{bulls}A{cows}B"
            skt.send(response.encode())

            if bulls == 4:
                print(f"You lose. Server guess counts: {server_attempts}")
                break

def server(skt):
    # print("I am game2 server!")
    """伺服器邏輯"""
    server_secret = input("Please enter your secret number (4 different digits): ")
    server_attempts, client_attempts = 0, 0

    while True:
        # 接收客戶端的猜測
        client_guess = skt.recv(1024).decode()
        if len(client_guess) == 0:
            print("Another player disconnects.")
            return
        client_attempts += 1
        bulls, cows = calculate_bulls_and_cows(server_secret, client_guess)
        client_response = f"{bulls}A{cows}B"
        if client_response == "4A0B":
            skt.send(b"win")
            print(f"client wins! Guess counts: {client_attempts}")
            break
        else:
            skt.send(client_response.encode())
            print(f"client's guess: {client_guess}, reply: {client_response}")
            _ = skt.recv(1024).decode() # my turn msg
            if len(_) == 0:
                print("Another player disconnects.")
                return
            # 伺服器的猜測
            server_guess = input("Please enter your guess (4 different digits): ")
            skt.send(server_guess.encode())
            server_attempts += 1

            # 接收客戶端的回應
            server_response = skt.recv(1024).decode()
            if len(server_response) == 0:
                print("Another player disconnects.")
                return
            print(f"Your guess: {server_guess}, client reply: {server_response}")

            if "4A0B" in server_response:
                print(f"You win! Guess counts: {server_attempts}")
                # skt.send(b"win")
                break