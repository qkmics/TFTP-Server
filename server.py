#!/usr/bin/env python3
import socket
import sys
import _thread
import random
import struct
import threading
import os.path
from os import path

TIMEOUT = 0
MAX_RESEND_TIME = 10

def main():
    PORT = int(sys.argv[1])       # Port to listen on (non-privileged ports is 69)
          # Timeout time 

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('', PORT))
        while True:
            client_data, client_addr = s.recvfrom(1024) # buffer size is 1024 bytes
            _thread.start_new_thread(TFTP_Handle_Connection,(client_data,client_addr))

def TFTP_Send_Error_Msg(server_socket, client_addr, error_code, error_msg):
    opcode = 5   # Error Msg operation code
    print("sent ", error_msg)
    bytesToSend = struct.pack("!H", opcode)
    bytesToSend += struct.pack("!H", error_code)
    bytesToSend += error_msg.encode() 
    bytesToSend += b'\x00'
    server_socket.sendto(bytesToSend, client_addr)

def TFTP_Handle_Error_Msg(client_data):
    error_msg = client_data[4:-1].decode("ASCII")
    print("received ",error_msg)

def TFTP_Handle_RRQ(filename,client_addr):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    TIMEOUT = float(sys.argv[2])/1000
    server_socket.settimeout(TIMEOUT)

    server_port = random.randrange(1024,65535)
    while server_socket.bind(('', server_port)) == False:
        server_port = random.randrange(1024,65535)

    if(path.exists(filename) == False):
        TFTP_Send_Error_Msg(server_socket, client_addr, 1, "TFTP Error, File Not Found!")
        return

    f = open(filename,"br")

    client_TID = client_addr[1]   # The port of source address
    connect_terminate = False
    block = 0
    need_resend = False

    resend_times = 0

    while(connect_terminate == False):
        if(need_resend == False):
            send_data = f.read(512)
            block += 1
            resend_times = 0
            print("sent DATA",block)
        else:
            resend_times += 1
            if resend_times >= MAX_RESEND_TIME:           # If resend times exceed three, thread return and this connection terminates
                print(MAX_RESEND_TIME,resend_times,"Disconnect")
                return

        need_resend = False
        
        opcode = 3
        bytesToSend = struct.pack("!H", opcode)
        bytesToSend += struct.pack("!H", block)
        bytesToSend += send_data 
        server_socket.sendto(bytesToSend, client_addr)

        try:
            client_data, client_addr = server_socket.recvfrom(516) # buffer size is 516 bytes 

            # First, check the TID of sender
            if client_addr[1] != client_TID:
                print("ERROR, client_addr[1] != client_TID")
                TFTP_Send_Error_Msg(server_socket, client_addr, 5, "TFTP Error, Unknown Transfer Id!")

            ACK_opcode = struct.unpack("!H", client_data[0:2])[0]
            ACK_block = struct.unpack("!H", client_data[2:])[0]

            print("received ACK ", ACK_block)

            if(ACK_opcode == 5):
                TFTP_Handle_Error_Msg(client_data)
                return 

            if(ACK_opcode != 4):
                TFTP_Send_Error_Msg(server_socket, client_addr, 4, "TFTP Error, Illegal TFTP Operation!")
                print("ACK_opcode ERROR,",ACK_opcode,"NOT A ACK PACKET")
                return

            if(ACK_block != block):
                print("resent DATA",block)
                need_resend = True
        except socket.timeout:
            print("resent DATA",block)
            need_resend = True

def TFTP_Handle_WRQ(filename, client_addr):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    TIMEOUT = float(sys.argv[2])/1000
    server_socket.settimeout(TIMEOUT)

    server_port = random.randrange(1024,65535)
    while server_socket.bind(('', server_port)) == False:
        server_port = random.randrange(1024,65535)

    if(path.exists(filename) == True):
        TFTP_Send_Error_Msg(server_socket, client_addr, 6, "TFTP Error, File Already Exists!")
        return
    f = open(filename,"bw")

    client_TID = client_addr[1]   # The port of source address
    connect_terminate = False
    block = 0
    
    resend_times = 0
    while(connect_terminate == False):
        opcode = 4                  # operation code of ack
        bytesToSend = struct.pack("!H", opcode)
        bytesToSend += struct.pack("!H", block) 
        server_socket.sendto(bytesToSend, client_addr)
        print("sent ACK ",block)
        try:
            client_data, client_addr = server_socket.recvfrom(516) # buffer size is 516 bytes        

            # First, check the TID of sender
            if client_addr[1] != client_TID:
                print("ERROR, client_addr[1] != client_TID")
                TFTP_Send_Error_Msg(server_socket, client_addr, 5, "TFTP Error, Unknown Transfer Id!")

            data_opcode = struct.unpack("!H", client_data[0:2])[0]
            data_block = struct.unpack("!H", client_data[2:4])[0]
            receive_data = client_data[4:]

            print("received DATA ", data_block)

            if(data_opcode == 5):
                TFTP_Handle_Error_Msg(client_data)
                return 

            if(data_opcode != 3):
                print("DATA_opcode ERROR, NOT A DATA PACKET")
                TFTP_Send_Error_Msg(server_socket, client_addr, 4, "TFTP Error, Illegal TFTP Operation!")
                os.unlink(filename)
                return

            # If receive 
            if(data_block == block + 1):
                block = data_block
                f.write(receive_data)
                
            if len(receive_data) < 512 :
                bytesToSend = struct.pack("!H", opcode)
                bytesToSend += struct.pack("!H", block) 
                server_socket.sendto(bytesToSend, client_addr)
                print("sent ACK ",block)
                connect_terminate = True
            
            resend_times = 0
        except socket.timeout:
            print("resent ACK ",block)
            resend_times += 1
            if resend_times >= MAX_RESEND_TIME:
                print(MAX_RESEND_TIME,resend_times,"Disconnect")
                return

def TFTP_Handle_Connection(client_data,client_addr):
    opcode = struct.unpack("!H", client_data[:2])[0]
    pos = 2
    filename = ""
    while client_data[pos] != 0:
        filename += chr(client_data[pos])
        pos += 1

    if opcode == 1:
        print("Received RRQ:", client_data, client_addr)
        TFTP_Handle_RRQ(filename, client_addr)
    elif opcode == 2:
        print("Received WRQ:", client_data, client_addr)
        TFTP_Handle_WRQ(filename, client_addr)

if __name__ == "__main__":
    main()