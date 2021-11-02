import datetime
import os
import pathlib
import subprocess
import sys
import time
import yaml
from objects import Coin, Column, Stat

refresh_interval = 60
stat_folder = '/data/chia/stat'

coins = []

columns = [
    Column('name', 'Name', 15),
    Column('farm_plot_count', 'Plots', 6),
    Column('wallet_balance', 'Balance', 10),
    Column('farm_yesterday', 'Yesterday', 10),
    Column('farm_today', 'Today', 10),
    Column('farm_etw', 'Estimated time to win', 25),
    Column('farm_plot_size', 'Total plot size', 17),
    Column('network_space', 'Network space', 15),
    Column('node_status', 'Node', 10),
    Column('wallet_status', 'Wallet', 10),
    Column('farm_status', 'Farm', 10),
]


def uprint(*objects, sep=' ', end='\n', file=sys.stdout):
    enc = file.encoding
    if enc == 'UTF-8':
        print(*objects, sep=sep, end=end, file=file)
    else:
        f = lambda obj: str(obj).encode(enc, errors='backslashreplace').decode(enc)
        print(*map(f, objects), sep=sep, end=end, file=file)


def read_config(argv):
    global stat_folder, refresh_interval
    directory = pathlib.Path().resolve()
    file_name = 'config.yaml'
    for arg in argv:
        if arg.endswith('.yaml'):
            file_name = arg
    file_path = os.path.join(directory, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Unable to find the config.yaml file. Expected location: {file_path}")
    f = open(file_path, 'r')
    config = yaml.load(stream=f, Loader=yaml.Loader)
    f.close()

    stat_folder = config.get('stat_folder', None)
    refresh_interval = int(config.get('refresh_interval', '60'))
    for coin_dict in config.get('coins', None):
        coins.append(Coin(coin_dict['name'], coin_dict['command']))
    return config


def gether_stat(coin, stat_folder):
    if coin.command is not None and len(coin.command) > 0:
        out1, _ = subprocess.Popen([coin.command, 'show', '-s'], stderr=subprocess.PIPE, universal_newlines=True,stdout=subprocess.PIPE).communicate()
        out2, _ = subprocess.Popen([coin.command, 'wallet', 'show'], stderr=subprocess.PIPE, universal_newlines=True,stdout=subprocess.PIPE).communicate()
        out3, _ = subprocess.Popen([coin.command, 'farm', 'summary'], stderr=subprocess.PIPE, universal_newlines=True,stdout=subprocess.PIPE).communicate()
        p = subprocess.Popen([coin.command, 'wallet', 'get_transactions'], stdin=subprocess.PIPE,stderr=subprocess.PIPE, universal_newlines=True,stdout=subprocess.PIPE)
        p.stdin.write('c\n' * 1000) # '--no-paginate'
        out4, _ = p.communicate()

        stat_path = os.path.join(stat_folder, coin.name + '.txt')
        stat_file = open(stat_path, 'w')
        stat_file.write(out1)
        stat_file.write(out2)
        stat_file.write(out3)
        stat_file.write(out4)
        stat_file.close()
        

def format_number(num):
    if isinstance(num, float):
        num = '%s' % num
    if num.endswith('.0'):
        num = num[:-2]
    if len(num) > 6:
        num = num[0:6]
    return num

def parse_stat_file(coin, stat_folder):
    stat = Stat()
    stat.name = coin.name
    stat_path = os.path.join(stat_folder, coin.name + '.txt')
    if os.path.exists(stat_path):
        stat_file = open(stat_path, 'r')
        lines = stat_file.readlines()
        stat_file.close()
        stat.updated = os.path.getmtime(stat_path)

        # skip if the stat_file is not up-to-date
        struct_time = time.localtime(stat.updated)
        dt = datetime.datetime(*struct_time[:6])
        if dt + datetime.timedelta(minutes=5) > datetime.datetime.now():
            amount = None
            for line in lines:
                tokens = line.split()
                if line.startswith('Current Blockchain Status:'):
                    stat.node_status = ' '.join(tokens[3:])
                    if stat.node_status == 'Full Node Synced':
                        stat.node_status = 'Synced'
                if line.startswith('Sync status:'):
                    stat.wallet_status = ' '.join(tokens[2:])
                if line.startswith('   -Total Balance:'):
                    if len(stat.wallet_balance) == 0:
                        stat.wallet_balance = tokens[2]
                if line.startswith('Farming status:'):
                    stat.farm_status = ' '.join(tokens[2:])
                    if stat.farm_status == 'Not available':
                        stat.farm_status = ''
                if line.startswith('Plot count for all harvesters:'):
                    stat.farm_plot_count = tokens[-1]
                if line.startswith('Plot count:'):
                    stat.farm_plot_count = tokens[-1]
                if line.startswith('Total size of plots:'):
                    stat.farm_plot_size = ' '.join(tokens[4:])
                    if stat.farm_plot_size == 'Unknown':
                        stat.farm_plot_size = ''
                if line.startswith('Expected time to win:'):
                    stat.farm_etw = ' '.join(tokens[4:])
                    if stat.farm_etw == 'Unknown':
                        stat.farm_etw = ''
                    else:
                        stat.farm_etw = stat.farm_etw.replace('and ', '')
                if line.startswith('Estimated network space:'):
                    stat.network_space = ' '.join(tokens[3:])
                    if stat.network_space == 'Unknown':
                        stat.network_space = ''
                if line.startswith('Amount received:'):
                    amount = float(tokens[2])
                if line.startswith('Amount:'):
                    amount = float(tokens[1])
                if line.startswith('Created at:') and amount is not None:
                    created_date = tokens[2]
                    today = datetime.datetime.now().isoformat(' ').split()[0]
                    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(' ').split()[0]
                    if created_date == today:
                        if stat.farm_today == '':
                            stat.farm_today = amount
                        else:
                            stat.farm_today += amount
                    if created_date == yesterday:
                        if stat.farm_yesterday == '':
                            stat.farm_yesterday = amount
                        else:
                            stat.farm_yesterday += amount
                    amount = None
            stat.wallet_balance = format_number(stat.wallet_balance)
            stat.farm_yesterday = format_number(stat.farm_yesterday)
            stat.farm_today = format_number(stat.farm_today)
    return stat


def print_heading(columns):
    total_width = len(columns) - 1
    line = ''
    for column in columns:
        line += (('%-' + '%s' % column.width) + 's ') % column.heading
        total_width += column.width
    uprint(line)
    uprint('-' * total_width)


def print_stat(stat, columns):
    if stat is not None:
        line = ''
        for column in columns:
            token = ('%-' + ('%s' % column.width) + 's') % getattr(stat, column.id)[0:column.width]
            line += token + ' '
        uprint(line.strip())


def main(argv):
    read_config(argv)
    first = True
    try:
        updated = None
        while True:
            if not first:
                for coin in coins:
                    gether_stat(coin, stat_folder)
            if os.name == 'nt':
                os.system('cls')
            else:
                os.system('clear')
            print_heading(columns)
            for coin in coins:
                stat = parse_stat_file(coin, stat_folder)
                if stat is not None:
                    if updated is None:
                        updated = stat.updated
                    elif updated < stat.updated:
                        updated = stat.updated
                    print_stat(stat, columns)
            uprint('')
            uprint('Last updated: %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))))
            if first:
                first = False
            else:
                time.sleep(refresh_interval)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        uprint('%s %s' % (type(error), error))


if __name__ == "__main__":
    main(sys.argv[1:])
