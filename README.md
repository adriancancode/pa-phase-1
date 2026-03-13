# Programming Assignment Phase 1
Phase 1 of group programming for CPSC 471-13: Computer Communications
Members: Adrian Vazquez, Muhammad Shahwar Shamim, Saketh Kakarla, Jiles Smith, Brandon Lee

## How to setup
1. Clone repo:
```
git clone https://github.com/adriancancode/pa-phase-1.git
cd pa-phase-1
```

2. Create a folder in repo called "files".  This will allow you to access files to transfer.

3. Open up two terminals, one to run the server side (serv.py) and one to run the client side (client.py).

## How to run

1. On one terminal, travel into files folder and run the server side:

```
cd files && python3 ../serv.py <PORT_NUMBER>
```
Note: <PORT_NUMBER> HAS to be between 1024 and 65535.

Once you run the server side, you should see something like this:
```
==================================================
         Simple FTP Server — Phase 1
==================================================
  Host:      <Hostname>
  IP:        <IP Address>
  Port:      <PORT_NUMBER>
  Directory: <Directories to files>
==================================================
  Waiting for connections... (Ctrl+C to stop)
==================================================
```

2.  On the other terminal, travel into files folder and run the client side, connecting it to the hostname display and port number on the server side:

```
cd files && python3 ../client.py <Hostname> <PORT_NUMBER>
```

3. Run any of the following commands on client.py to transfer files across network.  All commands are sent as UTF-8 text lines (ending with \n):
  - put: client sends "put <filename>\n", waits for "OK\n", then 8-byte size + raw bytes
  - get: client sends "get <filename>\n", waits for "OK\n", then receives 8-byte size + raw bytes
  - ls:  server sends file list as text lines, terminated by "END\n"
  - quit: server replies "BYE\n" and closes connection

4. To quit server, Ctrl + C.
