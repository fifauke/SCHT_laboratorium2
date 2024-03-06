import csv
import json
import networkx as nx
import matplotlib.pyplot as plt

nodes = set()
weighed_connections = []
host_num_pair = {}
switch_pairs_with_ports = {}
switch_pairs_with_bw_weight = {}
switch_pairs_with_delay_weight = {}
pairs_added_to_json = []


def load_nodes():
    with open('nodes.txt', 'r') as file:
        for index, line in enumerate(file):
            node = line.strip()
            nodes.add(node)
            host_num_pair[node] = str(index + 1) if index + 1 < 10 else 'a'


def load_weighed_connections():
    with open('sw_flows.txt', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 5:
                host1, host2, distance, port1, port2 = row
                switch_pairs_with_bw_weight[host2 + '_' + host1] = 10
                switch_pairs_with_bw_weight[host1 + '_' + host2] = switch_pairs_with_bw_weight[host2 + '_' + host1]
                switch_pairs_with_delay_weight[host1 + '_' + host2] = int(distance)
                switch_pairs_with_delay_weight[host2 + '_' + host1] = switch_pairs_with_delay_weight[host1 + '_' + host2]
                switch_pairs_with_ports[host1 + '_' + host2] = {host1: port1, host2: port2}
                switch_pairs_with_ports[host2 + '_' + host1] = switch_pairs_with_ports[host1 + '_' + host2]


def find_best_path(start, end, block_rate, acceptable_loss, acceptable_delay):
    with open('sw_flows.txt', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 5:
                host1, host2, distance, port1, port2 = row
                available_bw = switch_pairs_with_bw_weight[host1 + '_' + host2]
                bw_weight = (1 - available_bw / block_rate) * 100 / acceptable_loss if available_bw < block_rate else 0
                delay_weight = switch_pairs_with_delay_weight[host1 + '_' + host2] / acceptable_delay
                total_weight = bw_weight + delay_weight
                weighed_connections.append((host1, host2, total_weight))
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from(weighed_connections)
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_color='lightgreen', font_weight='bold')
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=nx.get_edge_attributes(graph, 'weight'))
    plt.show()
    try:
        path = nx.dijkstra_path(graph, start, end)
        return path
    except:
        print("brak połączenia miedzy " + start + " i " + end)
        return


def create_json():
    with open("flows.json", "w") as file:
        file.write("{ \n \"flows\": [\n")


def host_to_self_switch_for_each():
    with open("flows.json", "a") as file:
        for i in range(1, len(host_num_pair) + 1, 1):
            device_id = "of:000000000000000" + str(i) if i < 10 else "of:000000000000000a"
            content = {
                "priority": 40000,
                "timeout": 0,
                "isPermanent": True,
                "deviceId": device_id,
                "treatment": {
                    "instructions": [
                        {
                            "type": "OUTPUT",
                            "port": 1
                        }
                    ]
                },
                "selector": {
                    "criteria": [
                        {
                            "type": "ETH_TYPE",
                            "ethType": "0x0800"
                        },
                        {
                            "type": "IPV4_DST",
                            "ip": f"10.0.0.{i}/32"
                        }
                    ]
                }
            }
            json.dump(content, file, indent=5)
            file.write(",")


def flows_between_switches(path, bw=5, is_last=False):
    with open("flows.json", "a") as file:
        for i in range(0, len(path), 1):
            city = path[i]
            for j in range(0, len(path), 1):
                if j == i:
                    continue
                target_city = path[j]
                if j > i:
                    next_city = path[i + 1]
                if j < i:
                    next_city = path[i - 1]
                if target_city == next_city:
                    switch_pairs_with_bw_weight[city + '_' + next_city] = switch_pairs_with_bw_weight[
                                                                              city + '_' + next_city] - bw if \
                        switch_pairs_with_bw_weight[city + '_' + next_city] - bw > 0 else 0.01
                if pairs_added_to_json.__contains__(target_city + '_' + city):
                    continue
                pairs_added_to_json.append(target_city + '_' + city)
                device_id = "of:000000000000000" + host_num_pair[city]
                ip_addr = f"10.0.0.{host_num_pair[target_city]}/32" if host_num_pair[
                                                                           target_city] != 'a' else '10.0.0.10/32'
                port = switch_pairs_with_ports[city + "_" + next_city][city]
                flow = {
                    "priority": 40000,
                    "timeout": 0,
                    "isPermanent": True,
                    "deviceId": device_id,
                    "treatment": {
                        "instructions": [
                            {
                                "type": "OUTPUT",
                                "port": port
                            }
                        ]
                    },
                    "selector": {
                        "criteria": [
                            {
                                "type": "ETH_TYPE",
                                "ethType": "0x0800"
                            },
                            {
                                "type": "IPV4_DST",
                                "ip": ip_addr
                            }
                        ]
                    }
                }
                json.dump(flow, file, indent=5)
                if j < len(path) - 2 or not i == len(path) - 1 or not is_last:
                    file.write(",")


def endFile():
    with open("flows.json", "a") as f:
        f.write("]\n}")


# def send():
#     headers = {
#         'Content-Type': 'application/json',
#         'Accept': 'application/json',
#     }
#     with open('flows.json') as f:
#         data = f.read()
#         response = requests.post('http://192.168.43.11:8181/onos/v1/flows', headers=headers, data=data,
#                                  auth=('karaf', 'karaf'))
#         print(response)


if __name__ == "__main__":
    block_rate = 8
    acceptable_loss = 20
    acceptable_delay = 100
    load_nodes()
    load_weighed_connections()
    paths = [['Warszawa', 'Kopenhaga']]
    create_json()
    host_to_self_switch_for_each()
    for a_path in paths:
        flows_between_switches(a_path, bw=5)
    path = find_best_path('Warszawa', 'Londyn', block_rate, acceptable_loss, acceptable_delay)
    print(path)
    flows_between_switches(path, bw=8, is_last=True)
    endFile()
    # send()
