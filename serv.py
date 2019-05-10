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
# Server side of FTP
# valid input calls:
#     ls: send the list of contents on the server directory to the requested port #
#     put: allocate an ephemeral port and inform the client and wait for data
#     get: send the requested file to to the assigned port # on the client side
#     quit: release the allocated resources and terminate the process
# ==========================================================================================
import socket
import sys
import os
# ==========================================================================================
# The maximum size of files allowed for transfer by this protocol (10 GB)
MAX_SIZE = 10000000
# ==========================================================================================
class Server:
    def __init__(self, port_num):
        # Create a welcome socket.
        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the port
        self.__server_sock.bind(('', int(port_num)))
        # Start listening on the socket
        self.__server_sock.listen(1)
        # private_var
        self.__terminate = False

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

    def start(self):
        print("Server ready to accept connections")
        print("Stop by pressing ctr + c")
        try:
            # Accept connections forever
            while not self.__terminate:
                # Accept connections
                client_sock, addr = self.__server_sock.accept()
                # print("a connection is received")
                file_data = ""
                while file_data != "quit":
                    file_size_buff = self.__recvall(client_sock, 10)
                    # invalid call by client, ignore it and wait for a new call
                    if len(file_size_buff) == 0:
                        client_sock.close()
                        continue
                    # Get the file size
                    file_size = int(file_size_buff)
                    # Get the file data
                    file_data = self.__recvall(client_sock, file_size)

                    file_data = file_data.split('|')
                    if file_data[0] == "get":
                        self.__get(client_sock, file_data[1], int(file_data[2]), addr[0])
                    elif file_data[0] == "put":
                        self.__put(client_sock, file_data[1])
                    elif file_data[0] == "ls":
                        self.__ls(int(file_data[1]), addr[0])
                    elif file_data[0] == "quit":
                        break
                    else:
                        print("Unexpected data received: " + str(file_data))
                # Close our side
                client_sock.close()
        except KeyboardInterrupt:
            self.__server_sock.close()

    def __ls(self, prt_num, addr):
        result = ""
        for elem in os.listdir("server_data/"):
            result += elem + '\n'

        # ready to send data
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.connect((addr, prt_num))

        # Read upto max allowed bytes of data if exist
        if MAX_SIZE < len(result):
            packet = result[0:MAX_SIZE]
        else:
            packet = result

        # Prepend the size of the data to the file data.
        file_data = self.__addheader(packet)
        # The number of bytes sent
        num_sent = 0
        # Send the data
        while len(file_data) > num_sent:
            num_sent += data_sock.send(file_data[num_sent:].encode('utf-8'))

        data_sock.close()

    def __put(self, client_sock, f_name):
        # allocate a data socket
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.bind(('', 0))
        data_socket.listen(1)

        # format: port number where data can be received
        msg = self.__addheader("{}".format(data_socket.getsockname()[1]))
        # send a message to server and request a file
        bytes_sent = 0
        while bytes_sent != len(msg):
            bytes_sent += client_sock.send(msg[bytes_sent:].encode(encoding='utf-8'))

        # Accept connection
        client_sock, addr = data_socket.accept()
        # Get the file size which is the first 10 bytes indicating the size of the file
        file_size = int(self.__recvall(client_sock, 10))
        # Get the file data
        file_data = self.__recvall(client_sock, file_size)

        # release the resources back
        data_socket.close()
        client_sock.close()
        # save the file
        file_obj = open("server_data/{}".format(f_name), 'w')
        file_obj.write(str(file_data))
        file_obj.close()

    def __get(self, client_sock, f_name, prt_num, addr):
        try:
            file_obj = open("server_data/{}".format(f_name), 'r')
            # send a file found status to the client
            status = self.__addheader('1')
            bytes_sent = 0
            while bytes_sent != len(status):
                bytes_sent += client_sock.send(status[bytes_sent:].encode(encoding='utf-8'))

            # ready to send data
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.connect((addr, prt_num))

            # read upto the max limit allowed
            file_data = file_obj.read(MAX_SIZE)
            # Prepend the size of the data to the file data.
            file_data = self.__addheader(file_data)
            # The number of bytes sent
            num_sent = 0
            # Keep sending until all is sent
            while len(file_data) > num_sent:
                num_sent += data_sock.send(file_data[num_sent:].encode('utf-8'))

            file_obj.close()
            data_sock.close()

        except FileNotFoundError:
            # send an error status to the client
            status = self.__addheader('0')
            bytes_sent = 0
            while bytes_sent != len(status):
                bytes_sent += client_sock.send(status[bytes_sent:].encode(encoding='utf-8'))

def main():
    if len(sys.argv) != 2:
        print("An error in the input argument detected.")
        exit(-1)

    server = Server(sys.argv[1])
    server.start()


if __name__ == '__main__': main()
