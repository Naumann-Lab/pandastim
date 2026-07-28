import subprocess
import sys
import json
# from pandastim.utils import Publisher, Subscriber


def main():
    return input(">>> ")


if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "interact":

        running = True
        # improv_protocol_pub = Publisher(ipPORT)

        while running:

            ui = main()

            print(ui)
            # improv_protocol_pub.socket.send_string("improv_details")
            # improv_protocol_pub.socket.send_pyobj(ui)



            if ui == "quit":
                running=False
                break
            

        
    else:

        # ipSOCK = json.loads(sys.argv[1])
        # ipPORT = ipSOCK["improv_protocol_socket"]

        subprocess.Popen([
            "gnome-terminal",
            "--",
            "python3",
            sys.argv[0],
            "interact"
        ])

        
