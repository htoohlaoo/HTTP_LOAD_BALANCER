import socket
import threading
import psutil

def start_backend_server(port):
    #create a tcp/ip socket
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server_socket:
        #bind the socket to the port
        server_socket.bind(('localhost',port))
        #listen for incoming connections
        server_socket.listen()
        print(f"backend server is running on {port}...\n")

        while(True):
            #accept a new connection from the client
            client_socket,client_addr = server_socket.accept()
            #receive the request from the client
            request_data = client_socket.recv(1024).decode()
            #log the incoming request
            print("Receive request from",client_socket.getpeername())
            print(request_data)
            port_variable = str(port)
            response = "HTTP/1.1 200 OK\r\n\r\nHello from Backend Server at Port :"+port_variable+"\n"
            print(psutil.cpu_percent(interval=1))
            client_socket.sendall(response.encode())
            #close the client socket
            client_socket.close()



ports = [8080,8090,8100]
for port in ports:
    thread = threading.Thread(target=start_backend_server,args=(port,))
    thread.start()

