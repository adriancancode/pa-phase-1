"""
FTP Server - serv.py
Usage: python serv.py <PORT_NUMBER>
Example: python serv.py 1234

Protocol:
  - All commands are sent as UTF-8 text lines (ending with \n)
  - Command format:  CMD [arg]
  - For 'put': client sends "put <filename>\n", then 8-byte size, then raw bytes
  - For 'get': server sends 8-byte size, then raw bytes (or "ERR\n" if not found)
  - For 'ls':  server sends file list as text, terminated by "END\n"
  - For 'quit': server closes the connection cleanly
"""

import socket
import os
import sys
import threading

# ── helpers ──────────────────────────────────────────────────────────────────

def recv_exact(conn, n):
    """Read exactly n bytes from socket, blocking until all arrive."""
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Client disconnected mid-transfer")
        data += chunk
    return data


def send_file(conn, filepath):
    """Send a file: 8-byte little-endian size header, then raw bytes."""
    filesize = os.path.getsize(filepath)
    conn.sendall(filesize.to_bytes(8, "little"))
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            conn.sendall(chunk)
    print(f"  [→] Sent '{filepath}' ({filesize} bytes)")


def recv_file(conn, filename):
    """Receive a file: read 8-byte size header, then save raw bytes."""
    size_data = recv_exact(conn, 8)
    filesize = int.from_bytes(size_data, "little")
    print(f"  [←] Receiving '{filename}' ({filesize} bytes) ...")
    received = 0
    with open(filename, "wb") as f:
        while received < filesize:
            chunk = conn.recv(min(4096, filesize - received))
            if not chunk:
                raise ConnectionError("Client disconnected during upload")
            f.write(chunk)
            received += len(chunk)
    print(f"  [✓] Saved '{filename}'")

# ── per-client handler ────────────────────────────────────────────────────────

def handle_client(conn, addr):
    """Handle one connected client in its own thread."""
    print(f"\n[+] Connection from {addr}")
    buffer = ""

    try:
        while True:
            # Read data until we have a complete newline-terminated command
            while "\n" not in buffer:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    print(f"[-] Client {addr} disconnected")
                    return
                buffer += data

            line, buffer = buffer.split("\n", 1)
            parts = line.strip().split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            print(f"  [CMD] {addr} → {line.strip()}")

            # ── ls ──────────────────────────────────────────────────────────
            if cmd == "ls":
                files = os.listdir(".")
                files = [f for f in files if os.path.isfile(f)]
                response = "\n".join(files) + "\nEND\n" if files else "END\n"
                conn.sendall(response.encode("utf-8"))

            # ── get ─────────────────────────────────────────────────────────
            elif cmd == "get":
                filename = arg.strip()
                if not filename:
                    conn.sendall(b"ERR No filename specified\n")
                elif not os.path.isfile(filename):
                    conn.sendall(f"ERR File '{filename}' not found\n".encode())
                else:
                    conn.sendall(b"OK\n")
                    send_file(conn, filename)

            # ── put ─────────────────────────────────────────────────────────
            elif cmd == "put":
                filename = arg.strip()
                if not filename:
                    conn.sendall(b"ERR No filename specified\n")
                else:
                    conn.sendall(b"OK\n")
                    recv_file(conn, filename)
                    conn.sendall(b"DONE\n")

            # ── quit ─────────────────────────────────────────────────────────
            elif cmd == "quit":
                conn.sendall(b"BYE\n")
                print(f"[-] {addr} sent quit")
                return

            # ── unknown ──────────────────────────────────────────────────────
            else:
                conn.sendall(f"ERR Unknown command '{cmd}'\n".encode())

    except (ConnectionError, BrokenPipeError) as e:
        print(f"[!] Connection error with {addr}: {e}")
    except Exception as e:
        print(f"[!] Unexpected error with {addr}: {e}")
    finally:
        conn.close()
        print(f"[x] Closed connection to {addr}")

# ── main server loop ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) != 2:
        print("Usage: python serv.py <PORT_NUMBER>")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
        if not (1024 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("[!] PORT_NUMBER must be an integer between 1024 and 65535")
        sys.exit(1)

    # Create TCP socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Allow quick restart without "Address already in use" error
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_sock.bind(("", port))
    server_sock.listen(5)

    print(f"[*] FTP Server listening on port {port}")
    print(f"[*] Serving files from: {os.path.abspath('.')}")
    print("[*] Waiting for connections... (Ctrl+C to stop)\n")

    try:
        while True:
            conn, addr = server_sock.accept()
            # Each client gets its own thread so multiple clients can connect
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[*] Server shutting down.")
    finally:
        server_sock.close()


if __name__ == "__main__":
    main()