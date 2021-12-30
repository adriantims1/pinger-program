import os
import sys
import struct
import time
import select
import socket
import binascii
import math

ICMP_ECHO_REQUEST = 8

def checksum(str):
    csum = 0
    countTo = (len(str) / 2) * 2

    count = 0
    while count < countTo:
        thisVal = ord(str[count+1]) * 256 + ord(str[count])
        csum = csum + thisVal
        csum = csum & 0xffffffffL
        count = count + 2

    if countTo < len(str):
        csum = csum + ord(str[len(str) - 1])
        csum = csum & 0xffffffffL

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    global rtt_min, rtt_max, rtt_sum, rtt_cnt
    timeLeft = timeout
    while 1==1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)
        #Fill in start
        icmpHeader = recPacket[20:28]
        type, code, checksum, packetID, sequence = struct.unpack('bbHHh', icmpHeader)

        #Fetch the ICMP header from the IP packet
        if packetID == ID and addr[0] == destAddr:
            rtt_cnt += 1
            doubleBytes = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + doubleBytes])[0]
            TTL = struct.unpack('b',recPacket[8:9])[0]
            rtt_min = min(timeReceived - timeSent, rtt_min)
            rtt_max = max(rtt_max, timeReceived - timeSent)
            rtt_sum += timeReceived - timeSent
            return "Reply from " + addr[0] + ": bytes=" + str(len(recPacket[20:])) + ' time=' + str(int((timeReceived - timeSent)*1000)) + 'ms TTL=' + str(TTL)
        #Fill in end

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum.
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        myChecksum = socket.htons(myChecksum) & 0xffff
        #Convert 16-bit integers from host to network byte order.
    else:
        myChecksum = socket.htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    #Both LISTS and TUPLES consist of a number of objects
    #which can be referenced by their position number within the object

def doOnePing(destAddr, timeout):
    icmp = socket.getprotobyname("icmp")
    #SOCK_RAW is a powerful socket type. For more details see: http://sock-raw.org/papers/sock_raw
    
    #Fill in start
    mySocket = socket.socket(socket.AF_INET,socket.SOCK_RAW,icmp)

    #Create Socket here

    #Fill in end
    
    myID = os.getpid() & 0xFFFF #Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)

    mySocket.close()
    return delay

def ping(host, timeout=1):
    global rtt_min, rtt_max, rtt_sum, rtt_cnt
    rtt_min = 99999999999999999
    rtt_max = -99999999999999999
    rtt_sum = 0
    rtt_cnt = 0
    cnt = 0
    #timeout=1 means: If one second goes by without a reply from the server,
    #the client assumes that either the client's ping or the server's pong is lost
    dest = socket.gethostbyname(host)
    print "Pinging "+ host + ' [' + dest + ']' + ' with ' + str(16) + ' bytes of data using Python:'
    #Send ping requests to a server separated by approximately one second
    try:
        while 1==1:
            cnt += 1
            print doOnePing(dest, timeout)
            time.sleep(1)
    except KeyboardInterrupt:
        if cnt != 0:
            print
            print 'Ping statistics for ' + dest
            print '\tPackets: Sent = ' + str(cnt) + ", Received = " + str(rtt_cnt) + ', Lost = ' + str(cnt-rtt_cnt) + ' (' + str(int(100.0 - rtt_cnt * 100.0 / cnt)) + '% loss)'
            # print str(cnt) +' packets transmitted, ' + str(rtt_cnt) + ' packets received, ' + str(100.0 - rtt_cnt * 100.0 / cnt) + '% packet loss'
            if rtt_cnt != 0:
                print 'Approximate round trip times in milli-seconds:'
                print '\tMinimum = ' + str(int(rtt_min * 1000)) + 'ms, Maximum = ' + str(int(rtt_max*1000)) + 'ms, Average = ' + str(int(rtt_sum / rtt_cnt * 1000)) + 'ms'
                # print 'round-trip min/avg/max: ' + str(rtt_min) +'/'+str(rtt_sum / rtt_cnt)+'/'+str(rtt_max)


ping(sys.argv[1])