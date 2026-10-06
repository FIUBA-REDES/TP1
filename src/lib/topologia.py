from mininet.topo import Topo
from mininet.link import TCLink


class MyTopo(Topo):
    "Simple topology example."

    def __init__(self):
        "Create custom topo."

        # Initialize topology
        Topo.__init__(self)

        # Add hosts and switches
        Cliente_1 = self.addHost('h1')
        Cliente_2 = self.addHost('h2')
        Cliente_3 = self.addHost('h3')
        Cliente_4 = self.addHost('h4')
        Servidor = self.addHost('h5')

        Switch = self.addSwitch('s3')

        # Add links
        self.addLink(Cliente_1, Switch, cls=TCLink, loss=5, delay='10ms')
        self.addLink(Cliente_2, Switch, cls=TCLink, loss=5, delay='10ms')
        self.addLink(Cliente_3, Switch, cls=TCLink, loss=5, delay='10ms')
        self.addLink(Cliente_4, Switch, cls=TCLink, loss=5, delay='10ms')
        self.addLink(Servidor, Switch, cls=TCLink, loss=5, delay='10ms')


topos = {'mytopo': (lambda: MyTopo())}
