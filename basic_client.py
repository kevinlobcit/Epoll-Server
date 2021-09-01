#!/usr/bin/python
from threading import Thread
import threading
import logging
import time
import sys

#need to install xlwt to run the spreadsheet maker
import xlwt #python -m pip install xlwt
from xlwt import Workbook

#logging.getLogger().handlers.clear()
#logging.basicConfig(filename='speed.log', format='%(message)s', encoding='utf-8', level=logging.DEBUG)

wb = Workbook()
sheet1 = wb.add_sheet('Sheet1')
sheet1.write(0,0, 'Thread Number')
sheet1.write(0,1, 'Requests')
sheet1.write(0,2, 'Data Transfered')
sheet1.write(0,3, 'Total Duration')
sheet1.write(0,4, 'Avg Response')

"""
Basic TCP echo client. Sends a default message string to data to the server, 
and print server's echo. User can also specify an IP and message string to
sent to the server. 

NOTE: Specify commnadline arguments as follows:

./echo-client.py [host]
or
./echo-client.py [host] [message]

"""

def clientThread(serverHost,serverPort,encmsg, threadNo, requestCount):
    sockobj = socket(AF_INET, SOCK_STREAM)      # Create a TCP socket object
    sockobj.connect((serverHost, serverPort))   # connect to server IP + port
    
    totalTransfer = 0
    totaldelay = 0
    totalRequests = 0
    totalDuration = 0
    durationStart = time.time()
    for i in range(requestCount):
        start = time.time()#measure start here
        totalTransfer += sys.getsizeof(encmsg)
        sockobj.send(encmsg)                      # send user message 
        data = sockobj.recv(1024)               # read server response
        end = time.time()#measure end here
        delay = end - start
        print("Responsetime:" + str(delay) + " Received From Server:", data.decode())
        totaldelay += delay
        totalRequests += 1
    durationEnd = time.time()
    totalDuration = durationEnd-durationStart
        
    avgResp = totaldelay/100.0 #average response tme
    #logging.debug("Thread:" + str(threadNo) + " DataTransfered:"+ str(totalTransfer) +"bytes " + " avgResponsetime:" + str(avgResp)) 
    sheet1.write(threadNo+1,0, str(threadNo))
    sheet1.write(threadNo+1,1, str(totalRequests))
    sheet1.write(threadNo+1,2, str(totalTransfer))
    sheet1.write(threadNo+1,3, str(totalDuration))
    sheet1.write(threadNo+1,4, str(avgResp))
    #get total average
    sockobj.close()          

import sys
from socket import *              
serverHost = 'localhost'        # Default IP to connect to
serverPort = 8000               # Default port number

threadCount = 100
requestCount = 100
 # requires bytes: b'' to convert to byte literal
if len(sys.argv) >= 2:       
    serverHost = sys.argv[1]    # User has provided a server IP at cmd line arg 1
    if len(sys.argv) > 2:       # User-defined thread count
        threadCount = int(sys.argv[2])
    if len(sys.argv) > 3:
        requestCount = int(sys.argv[3])
        
    print("ThreadCount:", threadCount, "RequestCount", requestCount)
    
    
    workers = []
    responsetime = []
    for n in range(threadCount):
        message = "comp8005 is a hard class to do" + "\n"  # Default text (ASCII) message n=thread number
        #message = "c" + str(n) + "\n"  # Default text (ASCII) message
        encmsg = message.encode()
        w = Thread(target=clientThread, args=(serverHost,serverPort,encmsg,n, requestCount))
        w.start()
        workers.append(w)
    for w in workers:
        w.join()

#ttlAvgDura=0
#ttlAvgResp=0
##sh = wb.sheet_by_index('Sheet1')
#for i in range(threadCount):
#    ttlAvgDura += sheet1.cell(threadCount+1, 3).value
#    ttlAvgResp += sheet1.cell(threadCount+1, 4).value
#ttlAvgDura = ttlAvgDura/threadCount
#ttlAvgResp = ttlAvgResp/threadCount
#sheet1.write(1,6, str(ttlAvgDura))
#sheet1.write(1,8, str(ttlAvgResp))

wb.save('clientstats.xls')

#51003 50037