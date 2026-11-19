import subprocess
import sys
import ast
from pandastim.utils import Request, Reply


def main():
    return input(">>> ")


if __name__ == "__main__":
    ipSOCK = None

    if len(sys.argv) > 1 and sys.argv[1] == "interact":

        running = True
        ipSOCK = sys.argv[2]
        improv_protocol_req = Request(ipSOCK)
        improv_protocol_req.socket.send_string("handshake")
        reply = improv_protocol_req.socket.recv_string()
        print(reply)


        while running:

            ui = main()

            if "{" in ui and "}" in ui :
                ui = ast.literal_eval(ui)
                print(ui)
            
            improv_protocol_req.socket.send_pyobj(ui)
            rep = improv_protocol_req.socket.recv_string()
            print(rep)


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

        print("LAUNCHED IMPROV PLACEHOLDER CLI")

        
