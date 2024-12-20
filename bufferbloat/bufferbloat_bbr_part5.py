from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import lg, info
from mininet.util import dumpNodeConnections
from mininet.cli import CLI

from subprocess import Popen, PIPE
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

from monitor import monitor_qlen
import random

import sys
import os
import math

#OBS: qperf, quiche-client e quiche-server estão na pasta bin

parser = ArgumentParser(description="Bufferbloat tests")
parser.add_argument('--bw-host', '-B',
                    type=float, 
                    help="Bandwidth of host links (Mb/s)",
                    default=1000)

parser.add_argument('--bw-net', '-b',
                    type=float,  
                    help="Bandwidth of bottleneck (network) link (Mb/s)",
                    required=True)

parser.add_argument('--delay',
                    type=int,
                    help="Link propagation delay (ms)",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    required=True)

parser.add_argument('--time', '-t',
                    help="Duration (sec) to run the experiment",
                    type=int,
                    default=10)

parser.add_argument('--maxq',
                    type=int,
                    help="Max buffer size of network interface in packets",
                    default=100)

# Linux uses CUBIC-TCP by default that doesn't have the usual sawtooth
# behaviour.  For those who are curious, invoke this script with
# --cong cubic and see what happens...
# sysctl -a | grep cong should list some interesting parameters.
parser.add_argument('--cong',
                    help="Congestion control algorithm to use",
                    default="reno")

# Expt parameters
args = parser.parse_args()

class BBTopo(Topo):
    "Simple topology for bufferbloat experiment."

    def build(self, n=11):
        # create n hosts

        host1 = self.addHost('h1')
        host2 = self.addHost('h2')

        demais_hosts = []
        for i in range(3,n+1): #vai até o n
        	a = self.addHost(f"h{i}")
        	demais_hosts.append(a)

        # Here I have created a switch.  If you change its name, its
        # interface names will change from s0-eth1 to newname-eth1.
        switch = self.addSwitch('s0') #
                                                          
        #aparentemente o delay é (ex:) '20ms'
        self.addLink(host1,switch, bw = args.bw_host, delay = f"{args.delay}ms", max_queue_size=args.maxq)
        #self.addLink(host1,switch, bw = args.bw_host, delay = args.delay, max_queue_size=args.maxq) 
        #self.addLink(switch, host2, bw = args.bw_net, delay = f"{args.delay}ms", max_queue_size=args.maxq) #colocar maxqueue aqui?

        sw1 = self.addSwitch('s1') #switch intermediário entre switch 0 e demais hosts
        self.addLink(switch, sw1, bw = args.bw_net, delay = f"{args.delay}ms", max_queue_size=args.maxq)

        self.addLink(sw1, host2, bw = args.bw_net, delay = f"{args.delay}ms", max_queue_size=args.maxq)
        
        for i in range(3,n+1):
        	host_i = demais_hosts[i-3]
        	self.addLink(sw1, host_i, bw = args.bw_net, delay = f"{args.delay}ms", max_queue_size=args.maxq)


# Simple wrappers around monitoring utilities.  You are welcome to
# contribute neatly written (using classes) monitoring scripts for
# Mininet!

def start_iperf(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    print("Starting qperf server...")
    # For those who are curious about the -w 16m parameter, it ensures
    # that the TCP flow is not receiver window limited.  If it is,
    # there is a chance that the router buffer may not get filled up.
    #server = h2.popen("iperf -s -w 16m")
    
    #server = h2.popen("./bin/qperf -s -p 4433 -iw 16000000")
    server = h2.popen("./bin/qperf -s -p 4433")  
    print("server ok")

    # TODO: Start the iperf client on h1.  Ensure that you create a
    # long lived TCP flow.
    #print(f"h2 IP: {h2.IP()}")

    #client = h1.popen(f"iperf -c {h2.IP()} -t {args.time}") 
    client = h1.popen(f"./bin/qperf -c {h2.IP()} -p 4433 -t {args.time}")  
    #(output, error) = client.communicate()
    #print(output)
    #print("\n\n")
    #print(error)
    print("client ok")
    # preciso setar a window(-w)? 
    #o 300 é pra que o fluxo TCP seja de 300 segundos=5 minutos
    #acho que isso é longo o suficiente
    #obs: o produto delay x banda (do link gargalo), que limita window size seria
      #1.5Mb/s * 0.02s = 30 Kb 
    # preciso especificar a porta aqui (5001)? 

def start_qmon(iface, interval_sec=0.1, outfile="q.txt"):
    monitor = Process(target=monitor_qlen,
                      args=(iface, interval_sec, outfile))
    monitor.start()
    return monitor

def start_ping(net):
    # TODO: Start a ping train from h1 to h2 (or h2 to h1, does it
    # matter?)  Measure RTTs every 0.1 second.  Read the ping man page
    # to see how to do this.
    h1 = net.get('h1')
    h2 = net.get('h2')
    proc = h1.popen(f'ping {h2.IP()} -i 0.1 > {args.dir}/ping.txt', shell=True)
    return proc

def start_webserver(net):
    h1 = net.get('h1')
    proc = h1.popen("python webserver.py", shell=True)
    #proc = h1.popen("./bin/quiche-server --cert apps/src/bin/cert.crt --key apps/src/bin/cert.key --root .", shell=True)
    #proc = h1.popen(f"./bin/quiche-server --cert cert.crt --key cert.key --listen {h1.IP()}:4433 --root . --congestion bbr", shell=True)
    #proc = h1.popen("./../../quiche/target/release/quiche-server --cert cert.crt --key cert.key --root .", shell=True) 
    #cargo run --release --bin quiche-server -- --cert apps/src/bin/cert.crt --key apps/src/bin/cert.key --root bufferbloat (????)
    sleep(1)
    return [proc]

def fetch_html(net):
    h1 = net.get('h1')
    h2 = net.get('h2')
    #proc = h2.popen(f"curl --http3 -o /dev/null -s -w %{{time_total}} {h1.IP()}") #--http3?
    
    time_init = time()
    proc = h2.popen(f"curl -o /dev/null -s -w %{{time_total}} {h1.IP()} ")  
    #proc = h2.popen(f"./bin/quiche-client https://{h1.IP()}:4433 --no-verify --congestion bbr")
    #proc = h2.popen(f"./../../quiche/target/release/quiche-client https://{h1.IP()}:4433 --no-verify")
    
    #cargo run --release --bin quiche-client -- {h1.IP}:4433 --no-verify  
    (output, error) = proc.communicate() #esse output ta saindo como "" (string vazia)
    time_final = time()
    delta = time_final-time_init

    #if(int(time()) % 9 == 0): #aleatoriamente
    #    print("\noutput:\n")
    #    print(output)
    #    print("\n")
        
    #return float(output)
    return delta

#acho que não vou usar esse
def fetch(net, host_num):

    #host_num é o número do cliente

    h1 = net.get('h1') #servidor
    h2 = net.get(f"h{host_num}") 
    #proc = h2.popen(f"curl --http3 -o /dev/null -s -w %{{time_total}} {h1.IP()}") #--http3?

    #escolhendo o arquivo
    num = random.randint(1,5)
    
    extensao = "jpg"
    ext = random.randint(0,1)
    if(ext ==0):
        extensao = "txt"

    filename = f"f{num}.{extensao}"
    
    time_init = time()
    proc = h2.popen(f"curl -o /dev/null -s -w %{{time_total}} {h1.IP()} ")  
    #proc = h2.popen(f"./bin/quiche-client https://{h1.IP()}:4433/part5/{filename} --no-verify")
    #proc = h2.popen(f"./../../quiche/target/release/quiche-client https://{h1.IP()}:4433 --no-verify")
    
    #cargo run --release --bin quiche-client -- {h1.IP}:4433 --no-verify  
    (output, error) = proc.communicate() #esse output ta saindo como "" (string vazia)
    time_final = time()
    delta = time_final-time_init

    #if(int(time()) % 9 == 0): #aleatoriamente
    #    print("\noutput:\n")
    #    print(output)
    #    print("\n")
        
    #return float(output)
    return delta


def fetch_files(net, n):

    #n é o número de hosts que vão requerer um arquivo


    h1 = net.get('h1') #servidor
    clients = []

    for i in range(n): #lembrando que os hosts começam como 'h2'

        host = net.get(f"h{i+2}")
        clients.append(host)

    #proc = h2.popen(f"curl --http3 -o /dev/null -s -w %{{time_total}} {h1.IP()}") #--http3?
    
    processos = []
    start_times = []  
    for i in range(n): #cada host vai pedir um arquivo

        #escolhendo o arquivo
        num = random.randint(1,5)
    
        extensao = "jpg"
        ext = random.randint(0,1)
        if(ext ==0):
            extensao = "txt"

        filename = f"f{num}.{extensao}"

        host = clients[i]
    
        proc = host.popen(f"curl -o /dev/null -s -w %{{time_total}} {h1.IP()}/part5/{filename} ")  
        #proc = host.popen(f"time curl -o /dev/null -s {h1.IP()}/part5/{filename} ")
        #(output, error) = proc.communicate() 
        #proc = host.popen(f"time ./bin/quiche-client https://{h1.IP()}:4433/part5/{filename} --no-verify ")
        processos.append(proc)
        sleep(0.1) #aumentar esse sleep?

        #proc = h2.popen(f"./../../quiche/target/release/quiche-client https://{h1.IP()}:4433 --no-verify")
    
        #cargo run --release --bin quiche-client -- {h1.IP}:4433 --no-verify  

    deltas = []
    for i in range(n):
        proc = processos[i]
        (output, error) = proc.communicate() 
        delta=float(output)
        deltas.append(delta)

        #time_final = time()
        #delta = time_final-time_init
        #deltas.append(delta)

        #if(int(time()) % 9 == 0): #aleatoriamente
        #    print("\noutput:\n")
        #    print(output)
        #    print("error:\n", error)
        #    print("\n")

    
        
    #return float(output)
    return deltas


def bufferbloat():
    
    if not os.path.exists(args.dir):
        os.makedirs(args.dir)
    os.system("sysctl -w net.ipv4.tcp_congestion_control=%s" % args.cong)
    topo = BBTopo()
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)

    net.start()
    # This dumps the topology and how nodes are interconnected through
    # links.
    dumpNodeConnections(net.hosts)
    # This performs a basic all pairs ping test.
    net.pingAll()

    # TODO: Start monitoring the queue sizes.  Since the switch I
    # created is "s0", I monitor one of the interfaces.  Which
    # interface?  The interface numbering starts with 1 and increases.
    # Depending on the order you add links to your network, this
    # number may be 1 or 2.  Ensure you use the correct number.
    qmon = start_qmon(iface='s0-eth2',
                      outfile='%s/q.txt' % (args.dir))

    # TODO: Start iperf, webservers, etc.
    #start_iperf(net)
    #sleep(50) 
    #start_ping(net)
    start_webserver(net)

    # TODO: measure the time it takes to complete webpage transfer
    # from h1 to h2 (say) 3 times.  Hint: check what the following
    # command does: curl -o /dev/null -s -w %{time_total} google.com
    # Now use the curl command to fetch webpage from the webserver you
    # spawned on host h1 (not from google!)
    # Hint: Verify the url by running your curl command without the
    # flags. The html webpage should be returned as the response.


    # Hint: have a separate function to do this and you may find the
    # loop below useful.
    #start_time = time()
    soma_rtts = 0
    lista_rtts = []
    loops = 10 #numero de vezes que vou mandar todos os hosts fazerem fetch
    num_hosts = 10 #tem que ser no máximo  igual a n-1 em relação ao n do build da classe BBTopo
    n= loops*num_hosts


    #ToDo: fazer um for de 15, dando fetch_files,
    #e recebendo a lista de latencias
    #lembrando que agora eu sei o valor de n (a quantidade total de feths realizados) 
    #e vai rolar um lista_rtts.extend(latencias)
    print("starting clients...")
    for i in range(loops):
        latencias = fetch_files(net, num_hosts)
        print("Latencias: ", latencias)
        lista_rtts.extend(latencias)
        soma_rtts += sum(latencias)

        #o sleep já está dentro de fetch_files
  
    #now = time()
    #delta = now - start_time
    #if delta > args.time:
    #    break
    #print("%.1fs left..." % (args.time - delta))

    avg = soma_rtts/n
    print("media: "+str(avg))
    
    aux = 0
    numerador = 0
    for rtt in lista_rtts:
        aux = (rtt - avg)**2
        numerador += aux

    dev = math.sqrt(numerador/n)

    print("desvio padrao: "+str(dev))
    
    # TODO: compute average (and standard deviation) of the fetch
    # times.  You don't need to plot them.  Just note it in your
    # README and explain.

    # Hint: The command below invokes a CLI which you can use to
    # debug.  It allows you to run arbitrary commands inside your
    # emulated hosts h1 and h2.
    #CLI(net)

    qmon.terminate()
    net.stop()
    # Ensure that all processes you create within Mininet are killed.
    # Sometimes they require manual killing.
    Popen("pgrep -f webserver.py | xargs kill -9", shell=True).wait()
 
if __name__ == "__main__":
    bufferbloat()
