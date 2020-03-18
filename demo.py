import sys
import nnpy

def main():
    addr = "tcp://127.0.0.1:8000"
    s1 = nnpy.Socket(nnpy.AF_SP, nnpy.REQ)
    s2 = nnpy.Socket(nnpy.AF_SP, nnpy.REP)

    s1.bind(addr)
    s2.connect(addr)

    s1.send(b"HELLO")
    s2.recv()

    s2.send(b"ACK")
    res = s1.recv()
    print("{}\nres:{}", sys.version, res)


if __name__ == '__main__':
    main()

