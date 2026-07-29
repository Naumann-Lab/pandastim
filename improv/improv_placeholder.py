import subprocess
import sys
import json
from pandastim.utils import Publisher, Subscriber


def main():
    return input(">>> ")


if __name__ == "__main__":
    ipSOCK = None

    if len(sys.argv) > 1 and sys.argv[1] == "interact":

        running = True
        ipSOCK = sys.argv[2]
        improv_protocol_pub = Publisher(ipSOCK)

        while running:

            ui = main()

            print(ui)
            improv_protocol_pub.socket.send_string("improv_details")
            improv_protocol_pub.socket.send_pyobj(ui)



            if ui == "quit":
                running=False
                break
            

        
    else:

        ipSOCK = sys.argv[1]

        subprocess.Popen([
            "cmd",
            "/k",
            "start",
            "python",
            sys.argv[0],
            "interact",
            ipSOCK
        ])

        print("LAUNCHED")

        
