from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8
timeRTT = []
packageSent = 0
packageRev = 0


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = ord(string[count+1]) * 256 + ord(string[count])
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2

    if countTo < len(string):
        csum = csum + ord(string[len(string) - 1])
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

errMsg = {
    0: "0: Destination Network  Unreachable",
    1: "1: Destination Host Unreachable",
    2: "2: Destination Protocol Unreachable",
    3: "3: Destination Port Unreachable",
    4: "4: Fragmentation Required, and DF Flag Set",
    5: "5: Source Route Failed",
    6: "6: Destination Network Unknown",
    7: "7: Destination Host Unknown",
    8: "8: Source Host Isolated",
    9: "9: Network Administratively Prohibited",
    10: "10: Host Administratively Prohibited",
    11: "11: Network Unreachable for ToS",
    12: "12: Host Unreachable for ToS",
    13: "13: Communication Administratively Prohibited",
    14: "14: Host Precedence Violation",
    15: "15: Precedence Cutoff in Effect"
}

def receiveOnePing(mySocket, ID, timeout, destAddr):
    global packageRev, timeRTT
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fill in start

        ICMPHeader = recPacket[20:28]
        Type, Code, Checksum, packetID, Sequence = struct.unpack(
            'bbHHh', ICMPHeader)
        if(Type == 3):
            print(errMsg.get(Code, "Unknown Destination Unreachable Error"))
        if packetID == ID:
            bytesInDouble = struct.calcsize('d')
            timeSent = struct.unpack(
                'd', recPacket[28:28 + bytesInDouble])[0]
            timeRTT.append(timeReceived - timeSent)
            packageRev += 1

            return timeReceived - timeSent
        else:
            return 'Different ID found'

        # Fill in end

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    global packageSent
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.

    myChecksum = checksum(str(header + data))

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
            # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    # AF_INET address must be tuple, not str
    mySocket.sendto(packet, (destAddr, 1))
    packageSent += 1
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.


def doOnePing(destAddr, timeout):
	icmp = getprotobyname("icmp")

	# SOCK_RAW is a powerful socket type. For more details:   http://sock-raw.org/papers/sock_raw
	mySocket = socket(AF_INET, SOCK_RAW, icmp)
    # except socket.error as e:
    #     if e.errno == 1:
    #         raise

	myID = os.getpid() & 0xFFFF  # Return the current process i
	sendOnePing(mySocket, destAddr, myID)
	delay = receiveOnePing(mySocket, myID, timeout, destAddr)
	
	mySocket.close()
	return delay


def ping(host, timeout=10):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("Pinging " + dest + " using Python:")
    print("")
    # Send ping requests to a server separated by approximately one second
    while 1:
        delay = doOnePing(dest, timeout)
        print("RTT: "+str(delay))
        print("MaxRTT:" + str(max(timeRTT) if len(timeRTT) > 0 else 0) + "\n"+"MinRTT:" + str((min(timeRTT) if len(
            timeRTT) > 0 else 0))+"\n"+"averageRTT:"+str(float(sum(timeRTT)/len(timeRTT) if len(timeRTT) > 0 else float("nan"))))
        print("Package Lose Rate:" + str(((packageSent - packageRev) /
                                          packageSent if packageRev > 0 else 0)))
        print("")
        time.sleep(1)  # one second
    return delay

ping("yahoo.co.jp")