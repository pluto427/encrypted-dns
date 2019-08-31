import random
import socket

from encrypted_dns import parse, upstream, utils


class Server:

    def __init__(self, dns_config_object):
        self.dns_config = dns_config_object.get_config()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dns_map = {}

    def check_config(self):
        bootstrap_dns_address = self.dns_config['bootstrap_dns_address']['address']
        bootstrap_dns_port = self.dns_config['bootstrap_dns_address']['port']

        for item in self.dns_config['upstream_dns']:
            if item['protocol'] == 'https' or item['protocol'] == 'tls':
                address = item['address'].lstrip('https://')
                address = address.rstrip('/dns-query')

                if not utils.is_valid_ipv4_address(address):
                    if 'ip' not in item or item['ip'] == '':
                        item['ip'] = self.get_ip_address(address, bootstrap_dns_address, bootstrap_dns_port)

    @staticmethod
    def get_ip_address(address, bootstrap_dns_address, bootstrap_dns_port):

        return ''

    def start(self):
        self.server.bind((self.dns_config['listen_address'], self.dns_config['listen_port']))

        while True:
            recv_data, recv_address = self.server.recvfrom(512)
            recv_header = parse.ParseHeader.parse_header(recv_data)
            print('recv_data:', recv_data)

            transaction_id = recv_header['transaction_id']
            print('transaction_id:', transaction_id)

            if recv_header['flags']['QR'] == '0':
                self.dns_map[transaction_id] = recv_address
                self.handle_query(recv_data)

            if recv_header['flags']['QR'] == '1':
                if transaction_id in self.dns_map:
                    sendback_address = self.dns_map[transaction_id]
                    self.server.sendto(recv_data, sendback_address)
                    self.dns_map.pop(transaction_id)
                else:
                    pass

                self.handle_response(recv_data)

    def _send(self, response_data, address):
        self.server.sendto(response_data, address)

    def handle_query(self, query_data):
        query_parser = parse.ParseQuery(query_data)
        parse_result = query_parser.parse_plain()
        print('parse_result:', parse_result)

        upstream_object = self.select_upstream()
        upstream_object.query(query_data)

    def select_upstream(self):
        upstream_dns_list = self.dns_config['upstream_dns']
        enable_weight = self.dns_config['upstream_weight']
        upstream_timeout = self.dns_config['upstream_timeout']
        weight_list = []

        if enable_weight:
            for item in upstream_dns_list:
                weight_list.append(item['weight'])
            upstream_dns = random.choice(upstream_dns_list, weight_list)
        else:
            upstream_dns = random.choice(upstream_dns_list)

        server = self.server
        protocol = upstream_dns['protocol']
        address = upstream_dns['address']
        port = upstream_dns['port']
        upstream_object = None

        if protocol == 'plain':
            upstream_object = upstream.PlainUpstream(server, address, upstream_timeout, port)
        elif protocol == 'https':
            upstream_object = upstream.HTTPSUpstream(server, self.dns_config['listen_port'], address, upstream_timeout)
        elif protocol == 'tls':
            upstream_object = upstream.TLSUpstream(server, self.dns_config['listen_port'], address,
                                                   upstream_timeout, port)

        return upstream_object

    @staticmethod
    def handle_response(self):
        pass
