#!/usr/bin/env python

#Simple epoll echo server 

from __future__ import print_function
from contextlib import contextmanager
import socket
import select

from threading import Thread
import threading

import errno
from time import sleep

import sys
import os

ServerPort = 8000   # Listening port
MAXCONN = 50000        # Maximum connections
BUFLEN = 1024         # Max buffer size
numthreads = 4

import logging
logging.getLogger().handlers.clear()
logging.basicConfig(filename='serverResult.log',format='%(message)s', encoding='utf-8', level=logging.DEBUG)
#----------------------------------------------------------------------------------------------------------------
# Main server function 
def EpollServer (socket_options, address):
    #setup server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # Allow multiple bindings to port
    server.bind(address)
    server.listen (MAXCONN)
    server.setblocking (0)
    server.setsockopt (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # Set socket to non-blocking
    print ("Listening on Port:",ServerPort)
    #setup the main listening epoll
    epollmain = select.epoll()
    epollmain.register(server.fileno(), select.EPOLLIN)

    #setup clientsd, clientrequest, serverresponse dictionaries and creating threads
    aDataTransfered = [] #holds dictionary of how much data the server sends back
    aRequestCounts = [] #holds dictionary of how many requests the clients made
    aIpAddr = [] #holds dictionary of ip address
    
    epolls = []
    aClient_SDs = []
    aClient_Reqs = []
    aServer_Responses = []
    workers = []
    for i in range(numthreads):
        epollth = select.epoll()
        epolls.append(epollth)
        Client_SD = {}
        aClient_SDs.append(Client_SD)
        Client_Reqs = {}
        aClient_Reqs.append(Client_Reqs)
        Server_Responses = {}
        aServer_Responses.append(Server_Responses)
        ##############################################LOGGING
        #data collectors
        dataTransfered = {}
        aDataTransfered.append(dataTransfered)
        RequestCounts = {}
        aRequestCounts.append(RequestCounts)
        IpAddr = {}
        aIpAddr.append(IpAddr)
        ##############################################LOGGING
        w = Thread(target=workthread, args=(server, aClient_SDs[i], aClient_Reqs[i], aServer_Responses[i], epolls[i], aDataTransfered[i], aRequestCounts[i], aIpAddr[i]))
        workers.append(w)

    for w in workers:
        w.start()
        
    #do distributing the epoll initial connection fds to the threads    
    counter = 0
    server_SD = server.fileno()
    while True:
        events = epollmain.poll(1)
        for sockdes, event in events:
            if sockdes == server_SD:
                #give the fd to a worker thread
                init_connection (server, aClient_SDs[counter], aClient_Reqs[counter], aServer_Responses[counter], epolls[counter], aDataTransfered[counter], aRequestCounts[counter], aIpAddr[counter])
                counter = (counter+1)%numthreads #cycle the counter to evenly distribute connections
     
    #join back workers to close
    for w in workers:
        w.join()
    #closing all the epolls
    for epoll in epolls:
        epoll.close()
    epollmain.unregister(server.fileno())
    epollmain.close()
    #close server socket
    server.close()

# Process Client Connections new
def init_connection (server, Client_SD, Client_Reqs, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr):
    connection, address = server.accept()
    connection.setblocking(1)
    print ('Client Connected:', address)    #print client IP
    fd = connection.fileno()
    
    #give the fd to a thread and register the information
    epoll.register(fd, select.EPOLLIN)
    Client_SD[fd] = connection
    Server_Response[fd] = ''
    Client_Reqs[fd] = ''
    ################################# LOGGING
    DataTransfered[fd] = 0
    RequestCounts[fd] = 0
    IpAddr[fd] = address
    ################################# LOGGING

def workthread(server, Client_SD, Client_Reqs, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr):
    server_SD = server.fileno()
    
    totalreceive = 0
    totalsend = 0

    while True:
        events = epoll.poll(1)
        for sockdes, event in events:
            if sockdes in Client_SD: #chekc if the sockdes is in the dictionary
                if event & select.EPOLLIN: #respond to conneections that this worker has epoll registered to
                    Receive_Message (sockdes, Client_Reqs, Client_SD, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr)
                elif event & select.EPOLLOUT: #respond to conneections that this worker has epoll registered to
                    Echo_Response (sockdes, Client_SD, Server_Response, epoll, DataTransfered, RequestCounts)
#----------------------------------------------------------------------------------------------------------------
# Receive a request and send an ACK with echo
def Receive_Message (sockdes, Client_Reqs, Client_SD, Server_Response, epoll, DataTransfered, RequestCounts, IpAddr):
    temp = Client_SD[sockdes].recv(BUFLEN)
    Client_Reqs[sockdes] += temp.decode() #ADDED FIX HERE

    # Make sure client connection is still open    
    if Client_Reqs[sockdes] == 'quit\n' or Client_Reqs[sockdes] == '':
        print('[{:02d}] Client Connection Closed!'.format(sockdes))
        ##################################Output final logs
        logging.debug("IP:" + str(IpAddr[sockdes]) + ", FD:" + str(sockdes) + ", DataTransfered:" + str(DataTransfered[sockdes]) + ", RequestCount:" + str(RequestCounts[sockdes])) 
        ##################################Output final logs
        epoll.unregister(sockdes)
        Client_SD[sockdes].close()
        del Client_SD[sockdes], Client_Reqs[sockdes], Server_Response[sockdes]
        del DataTransfered[sockdes], RequestCounts[sockdes], IpAddr[sockdes]
        return

    elif '\n' in Client_Reqs[sockdes]:
        epoll.modify(sockdes, select.EPOLLOUT)
        msg = Client_Reqs[sockdes][:-1]
        ################################### increase request counts for the fd
        RequestCounts[sockdes] += 1
        ################################### LOGGING
        print(str(threading.get_ident()) + "[{:02d}] Received Client Message: {}".format (sockdes, msg))
        # ACK + received string
        #Server_Response[sockdes] = 'ACK => ' + Client_Reqs[sockdes]
        Server_Response[sockdes] = Client_Reqs[sockdes]
        Client_Reqs[sockdes] = ''
#----------------------------------------------------------------------------------------------------------------
# Send a response to the client
def Echo_Response (sockdes, Client_SD, Server_Response, epoll, DataTransfered, RequestCounts):
    temp = Server_Response[sockdes].encode()
    ####################################### record data amount sent
    DataTransfered[sockdes] += sys.getsizeof(temp)
    ####################################### LOGGING
    print(str(threading.get_ident()) + "[{:02d}] Sending Client Message: {}".format (sockdes, Server_Response[sockdes]))
    byteswritten = Client_SD[sockdes].send(temp)
    #byteswritten = Client_SD[sockdes].send(Server_Response[sockdes])
    Server_Response[sockdes] = Server_Response[sockdes][byteswritten:]
    epoll.modify(sockdes, select.EPOLLIN)
    
    #####print ("Response Sent")
#----------------------------------------------------------------------------------------------------------------
# Start the epoll server & Process keyboard interrupt CTRL-C
if __name__ == '__main__':
    try:
        EpollServer ([socket.AF_INET, socket.SOCK_STREAM], ("0.0.0.0", ServerPort))
    except KeyboardInterrupt as e:
        print("Server Shutdown")
        exit()      # Don't really need this because of context managers