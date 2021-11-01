import datetime
import os
import subprocess
import sys
import time
from objects import Coin, Column, Stat

refresh_interval = 60
stat_folder = '/data/chia/stat'

coins = [
    Coin('Chia XCH', '/usr/lib/chia-blockchain/resources/app.asar.unpacked/daemon/chia'),
    Coin('Chives XCC', None),
    Coin('Flax XFX', '/usr/lib/flax-blockchain/resources/app.asar.unpacked/daemon/flax'),
    Coin('HDD coin', '/usr/lib/hddcoin-blockchain/resources/app.asar.unpacked/daemon/hddcoin'),
    Coin('Skynet XNT', '/usr/lib/skynet-blockchain/resources/app.asar.unpacked/daemon/skynet'),
    Coin('STAI coin', '/usr/lib/staicoin-blockchain/resources/app.asar.unpacked/daemon/staicoin'),
]

columns = [
    Column('name', 'Name', 15),
    Column('farm_plot_count', 'Plots', 6),
    Column('wallet_balance', 'Balance', 10),
    Column('farm_yesterday', 'Yesterday', 10),
    Column('farm_today', 'Today', 10),
    Column('farm_etw', 'Estimated Time to Win', 25),
    Column('network_space', 'Network Space', 15),
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


def gether_stat(coin, stat_folder):
    if coin.command is not None:
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
    stat_path = os.path.join(stat_folder, coin.name + '.txt')
    if os.path.exists(stat_path):
        stat_file = open(stat_path, 'r')
        lines = stat_file.readlines()
        stat_file.close()
        stat = Stat()
        stat.name = coin.name
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
            if line.startswith('Expected time to win:'):
                stat.farm_etw = ' '.join(tokens[4:])
                if stat.farm_etw == 'Unknown':
                    stat.farm_etw = ''
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
                today = datetime.date.today()
                yesterday = datetime.date.today() - datetime.timedelta(days=1)
                today = '%s-%2s-%2s' % (today.year, today.month, today.day)
                yesterday = '%s-%2s-%2s' % (yesterday.year, yesterday.month, yesterday.day)
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
    return None


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
    first = True
    try:
        while True:
            if not first:
                for coin in coins:
                    gether_stat(coin, stat_folder)
            os.system('clear')
            print_heading(columns)
            for coin in coins:
                print_stat(parse_stat_file(coin, stat_folder), columns)
            uprint('')
            uprint('Last updated: %s' % (datetime.datetime.now()))
            if first:
                first = False
            else:
                time.sleep(refresh_interval)
    except:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])
