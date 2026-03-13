"""
FTP Client - client.py
Usage: python client.py <server_machine> <server_port>
Example: python client.py ecs.fullerton.edu 1234

Protocol (matches serv.py):
  - All commands are sent as UTF-8 text lines (ending with \n)
  - For 'put': client sends "put <filename>\n", waits for "OK\n", then 8-byte size + raw bytes
  - For 'get': client sends "get <filename>\n", waits for "OK\n", then receives 8-byte size + raw bytes
  - For 'ls':  server sends file list as text lines, terminated by "END\n"
  - For 'quit': server replies "BYE\n" and closes connection
"""

import socket
import os
import sys


# ── helpers ───────────────────────────────────────────────────────────────────

def recv_exact(sock, n):
    """Read exactly n bytes from socket, blocking until all arrive."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Server disconnected mid-transfer")
        data += chunk
    return data


def recv_line(sock, buffer):
    """
    Read from sock until we have a complete '\n'-terminated line.
    Returns (line_without_newline, remaining_buffer).
    """
    while "\n" not in buffer:
        chunk = sock.recv(1024).decode("utf-8")
        if not chunk:
            raise ConnectionError("Server disconnected")
        buffer += chunk
    line, _, buffer = buffer.partition("\n")
    return line.strip(), buffer


def send_file(sock, filepath):
    """Send a file: 8-byte little-endian size header, then raw bytes."""
    filesize = os.path.getsize(filepath)
    sock.sendall(filesize.to_bytes(8, "little"))
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            sock.sendall(chunk)
    print(f"  [→] Uploaded '{filepath}' ({filesize} bytes)")


def recv_file(sock, filename):
    """Receive a file: read 8-byte size header, then save raw bytes."""
    size_data = recv_exact(sock, 8)
    filesize = int.from_bytes(size_data, "little")
    print(f"  [←] Downloading '{filename}' ({filesize} bytes) ...")
    received = 0
    try:
        with open(filename, "wb") as f:
            while received < filesize:
                chunk = sock.recv(min(4096, filesize - received))
                if not chunk:
                    raise ConnectionError("Server disconnected during download")
                f.write(chunk)
                received += len(chunk)
    except OSError as e:
        if e.errno == 28:  # errno 28 = No space left on device
            print(f"  [!] Disk full — could not save file")
        else:
            print(f"  [!] File write error: {e}")
    print(f"  [✓] Saved '{filename}'")


# ── command handlers ──────────────────────────────────────────────────────────

def do_ls(sock, buffer):
    """Send 'ls', print the file list returned by the server."""
    sock.sendall(b"ls\n")
    files = []
    while True:
        line, buffer = recv_line(sock, buffer)
        if line == "END":
            break
        files.append(line)
    if files:
        print("Files on server:")
        for f in files:
            print(f"  {f}")
    else:
        print("  (no files on server)")
    return buffer


def do_get(sock, buffer, filename):
    """Send 'get <filename>', then receive the file if the server says OK."""
    sock.sendall(f"get {filename}\n".encode("utf-8"))
    response, buffer = recv_line(sock, buffer)
    if response.startswith("ERR"):
        print(f"  [!] Server error: {response}")
    elif response == "OK":
        recv_file(sock, filename)
    else:
        print(f"  [?] Unexpected server response: {response}")
    return buffer


def do_put(sock, buffer, filename):
    """Send 'put <filename>', then upload the file if the server says OK."""
    if not os.path.isfile(filename):
        print(f"  [!] Local file '{filename}' not found")
        return buffer
    sock.sendall(f"put {filename}\n".encode("utf-8"))
    response, buffer = recv_line(sock, buffer)
    if response.startswith("ERR"):
        print(f"  [!] Server error: {response}")
    elif response == "OK":
        send_file(sock, filename)
        # Wait for server's DONE acknowledgement
        done, buffer = recv_line(sock, buffer)
        if done == "DONE":
            print(f"  [✓] Server confirmed upload complete")
        else:
            print(f"  [?] Unexpected server response: {done}")
    else:
        print(f"  [?] Unexpected server response: {response}")
    return buffer


def do_quit(sock, buffer):
    """Send 'quit' and wait for BYE."""
    sock.sendall(b"quit\n")
    try:
        response, buffer = recv_line(sock, buffer)
        if response == "BYE":
            print("  Server said goodbye.")
    except ConnectionError:
        pass  # Server may have already closed
    return buffer


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 3:
        print("Usage: python client.py <server_machine> <server_port>")
        sys.exit(1)

    server_host = sys.argv[1]
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        print("[!] Port must be an integer")
        sys.exit(1)
    if  not (1024 <= server_port <= 65535):
            print("[!] Port must be between 1 and 65535")
            sys.exit(1)

    # Resolve hostname → IP (DNS lookup)
    try:
        server_ip = socket.gethostbyname(server_host)
        print(f"[*] Resolved {server_host} → {server_ip}")
    except socket.gaierror as e:
        print(f"[!] Could not resolve host '{server_host}': {e}")
        sys.exit(1)

    # Create TCP socket and connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(30)
        sock.connect((server_ip, server_port))
        print(f"[*] Connected to {server_host}:{server_port}")
    except ConnectionRefusedError:
        print(f"[!] Connection refused — is the server running on port {server_port}?")
        sys.exit(1)

    buffer = ""  # Accumulates partial data between reads

    try:
        while True:
            try:
                user_input = input("ftp> ").strip()
            except EOFError:
                # Ctrl+D
                do_quit(sock, buffer)
                break

            if not user_input:
                continue

            parts = user_input.split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "ls":
                buffer = do_ls(sock, buffer)

            elif cmd == "get":
                if not arg:
                    print("  Usage: get <filename>")
                else:
                    buffer = do_get(sock, buffer, arg)

            elif cmd == "put":
                if not arg:
                    print("  Usage: put <filename>")
                else:
                    buffer = do_put(sock, buffer, arg)

            elif cmd == "quit":
                do_quit(sock, buffer)
                break

            else:
                print(f"  [!] Unknown command '{cmd}'. Available: ls, get <file>, put <file>, quit")

    except (ConnectionError, BrokenPipeError) as e:
        print(f"\n[!] Connection lost: {e}")
    except KeyboardInterrupt:
        print("\n[*] Interrupted — sending quit...")
        try:
            do_quit(sock, buffer)
        except Exception:
            pass
    except socket.timeout:
        print("[!] Connection timed out the server is not responding")
        sys.exit(1)
    finally:
        sock.close()
        print("[*] Disconnected.")


if __name__ == "__main__":
    main()