class Coin:
    name = None
    command = None

    def __init__(self, name, command):
        self.name = name
        self.command = command


class Stat:
    name = ''
    node_status = ''
    wallet_status = ''
    wallet_balance = ''
    farm_status = ''
    farm_yesterday = ''
    farm_today = ''
    farm_plot_count = ''
    farm_plot_size = ''
    farm_etw = ''
    network_space = ''
    updated = None


class Column:
    id = ''
    heading = ''
    width = 10

    def __init__(self, id, heading, width):
        self.id = id
        self.heading = heading
        self.width = width

