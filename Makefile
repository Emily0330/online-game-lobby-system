# 定義需要刪除的檔案和目錄
CLIENT_DIR1 := client1_download
CLIENT_DIR2 := client2_download
CLIENT_DIR3 := client3_download
SERVER_DIR := server_game

# 定義目標
.PHONY: clean

# 刪除目標目錄下的所有 .py 檔案
clean:
	@echo "Cleaning up client and server directories..."
	rm -rf $(CLIENT_DIR1)/*
	rm -rf $(CLIENT_DIR2)/*
	rm -rf $(CLIENT_DIR3)/*
	rm -rf $(SERVER_DIR)/*
	@echo "Cleanup completed!"
