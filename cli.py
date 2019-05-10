#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ==========================================================================================
# Author: Mohammadreza Hajy Heydary
# Client side of FTP
# valid arguments:
#     ls: request the list of contents on the server directory along with allocate an
#         ephemeral port # where the result can be returned
#     put: send a put request to the server side along with a port where server returns
#          a message containing a port number where file can be sent to on the server
#     get: send a get request to the server along with an allocated ephemeral port where
#          server can send data
#     quit: release the allocated resources and terminate the process
# ==========================================================================================
import socket
import sys
# ==========================================================================================
# The maximum size of files allowed for transfer by this protocol (10 GB)
MAX_SIZE = 10000000
# ==========================================================================================
class Client:
    def __init__(self, prt_num, dm_name):
        # make a TCP socket
        self.__connSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__connSock.connect((dm_name, int(prt_num)))
        # private variables
        self.__domain = dm_name

    def __del__(self):
        self.__connSock.close()

    @staticmethod
    def __addheader(data):
        data_size = str(len(data))
        # Prepend 0's to the size string
        # until the size is 10 bytes
        while len(data_size) < 10:
            data_size = "0" + data_size

        # add the 10 bit message size header
        return data_size + data

    @staticmethod
    def __recvall(sock, num_bytes):
        recv_buff = ""
        tmp_buff = ""
        # Keep receiving till all is received
        while len(recv_buff) < num_bytes:
            # Attempt to receive bytes
            tmp_buff = sock.recv(num_bytes)
            # The other side has closed the socket
            if not tmp_buff:
                break

            # Add the received bytes to the buffer
            recv_buff += tmp_buff.decode(encoding='utf-8')

        return recv_buff

    def receive(self, file_name):
        # allocate a data socket
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.bind(('', 0))
        data_socket.listen(1)

        # format get|file_name|data_port_number
        msg = self.__addheader("get|{}|{}".format(file_name, data_socket.getsockname()[1]))
        # send a message to server and request a file
        bytes_sent = 0
        while bytes_sent != len(msg):
            bytes_sent += self.__connSock.send(msg[bytes_sent:].encode(encoding='utf-8'))

        # wait for server status code
        response_size = int(self.__recvall(self.__connSock, 10))
        # Get the response data which is the result of the ls query
        server_status = self.__recvall(self.__connSock, response_size)

        if int(server_status):
            # Accept connection
            client_sock, addr = data_socket.accept()
            # Get the file size which is the first 10 bytes indicating the size of the file
            file_size = int(self.__recvall(client_sock, 10))
            # Get the file data
            file_data = self.__recvall(client_sock, file_size)
            # release the resources
            client_sock.close()
            # save the file
            file_obj = open(file_name, 'w')
            file_obj.write(str(file_data))
            file_obj.close()
        else:
            print("File not found on the server")

        data_socket.close()

    def send(self, file_name):
        try:
            file_obj = open(file_name, 'r')
            # send a message to server and inform it about the upcoming file
            msg = self.__addheader("put|{}".format(file_name))
            # send a message to server and request a port
            bytes_sent = 0
            while bytes_sent != len(msg):
                bytes_sent += self.__connSock.send(msg[bytes_sent:].encode(encoding='utf-8'))

            # Get the file size which is the first 10 bytes indicating the size of the file
            file_size = int(self.__recvall(self.__connSock, 10))
            # Get the file data which is port number of data socket in server side
            file_data = self.__recvall(self.__connSock, file_size)

            # ready to send data
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((self.__domain, int(file_data)))

            # Read the appropriate amount of data
            file_data = file_obj.read(MAX_SIZE)
            # release the resource not needed anymore
            file_obj.close()

            # Prepend the size of the data to the file data.
            file_data = self.__addheader(file_data)
            # The number of bytes sent
            num_sent = 0
            # Send the data all
            while len(file_data) > num_sent:
                num_sent += data_sock.send(file_data[num_sent:].encode(encoding='utf-8'))

            # release the resources
            data_sock.close()

        except FileNotFoundError:
            print("File does not exist in the client directory")

    def ls(self):
        # allocate a data socket
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.bind(('', 0))
        data_socket.listen(1)

        # send a message to server and ask for the list of files
        msg = self.__addheader("ls|{}".format(data_socket.getsockname()[1]))
        bytes_sent = 0
        while bytes_sent != len(msg):
            bytes_sent += self.__connSock.send(msg[bytes_sent:].encode(encoding='utf-8'))

        # Accept connection
        client_sock, addr = data_socket.accept()
        # Get the file size which is the first 10 bytes indicating the size of the file
        file_size = int(self.__recvall(client_sock, 10))
        # Get the file data
        file_data = self.__recvall(client_sock, file_size)

        print(file_data)

    def quit(self):
        # send a message to server and ask for the list of files
        msg = self.__addheader("quit")
        bytes_sent = 0
        while bytes_sent != len(msg):
            bytes_sent += self.__connSock.send(msg[bytes_sent:].encode(encoding='utf-8'))

def main():
    if len(sys.argv) != 3:
        print("An error in the input argument detected.")
        exit(-1)

    client = Client(sys.argv[2], sys.argv[1])

    user_input = input("ftp> ")
    while True:
        # client = Client(1234, 'localhost')

        parsed_input = user_input.split()
        # invalid input, start again
        if len(parsed_input) == 0 or len(parsed_input) > 2:
            continue

        if parsed_input[0] == "get":
            if len(parsed_input) != 2:
                print("Invalid input for put command")
                print("valid format is: get <file_name>")
            else:
                client.receive(parsed_input[1])

        elif parsed_input[0] == "put":
            if len(parsed_input) != 2:
                print("Invalid input for put command")
                print("valid format is: put <file_name>")
            else:
                client.send(parsed_input[1])

        elif parsed_input[0] == "ls":
            client.ls()

        elif parsed_input[0] == "quit":
            # tell the server this client is done
            client.quit()
            # the connection shall be closed by the class destructor
            break

        user_input = input("ftp> ")


if __name__ == '__main__': main()
