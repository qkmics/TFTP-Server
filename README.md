# TFTP Server
    This is a TFTP server wroten in python3.
    The protocal specification is in RFC 1350.

## How to run the script
    In Linux : python3 server.py < port > < timeout >
    port is the server port number
    timeout is retransmission timeout(in milliseconds)

## Some problems I encountered
    When testing WRQ using tftp client in Linux, please set timeout a number greater than 5000 for floor control because the resend timeout of client is several seconds.

    When testing RRQ, since the tftp client would not send ACK of the last packet. The server would resend it for several times.
    Which is the same behavior as ACK lost. 

    When testing WRQ, the server send the ACK of the last packet only once.

