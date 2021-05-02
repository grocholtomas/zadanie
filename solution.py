from psycopg2.extras import Json
from config import config
from create_table import create_configurations_table

import psycopg2
import yaml


class InterfaceConfigurationsProcessor:
    """
        Class process extracts interface configurations from config json file and inserts important data to Postgres DB

        :param config: string of path to a config file that will be processed
        :param interfaces_to_process: list of important interfaces to be processed, if empty, it will process all of the interfaces configurations
	"""    
    def __init__(self, config : str, interfaces_to_process : list = []):        
        self.interfaces_to_process = interfaces_to_process
        self.config = config
        self.conn = self._connect_to_db() 
        self.cur = self.conn.cursor()

    def _connect_to_db(self):
        """
            Function uses config file and psycopg2 module to connect to Postgres DB specified in database.ini file
        """    
        params = config()
        return psycopg2.connect(**params)
    

    def _update_ethernet_port_channel_id(self):
        """
            Function updates port_channel_id column of ethernet interface configurations in configurations table
        """     
        port_channels = '''SELECT id, config from configurations WHERE name LIKE 'Port-channel%';'''
        ethernets = '''SELECT id, config from configurations WHERE name LIKE '%thernet%';'''
        update_port_channel_id = '''UPDATE configurations SET port_channel_id = %s WHERE id = %s'''

        try:
            self.cur.execute(ethernets)
            ethernets = self.cur.fetchall()            
            self.cur.execute(port_channels)
            port_channels = self.cur.fetchall()

            channel_ids = {}
            for port_channel in port_channels:
                channel_ids[port_channel[1]['name']] = port_channel[0]
            
            ethernets_to_update = []
            for ethernet in ethernets:
                if 'Cisco-IOS-XE-ethernet:channel-group' in ethernet[1].keys():
                    port_channel_id = channel_ids[ethernet[1]['Cisco-IOS-XE-ethernet:channel-group']['number']]
                    ethernets_to_update.append((port_channel_id, ethernet[0]))
            
            if ethernets_to_update:
                self.cur.executemany(update_port_channel_id, ethernets_to_update)
                self.conn.commit()
            else:
                print('No ethernet interface configurations found')

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            self.cur.close()
            self.conn.close()


    def _insert_data_list(self, values : list):          
        """
            Function inserts values to configurations table 
            :param values: list of values to be inserted
        """                   
        sql = '''
            INSERT INTO configurations (
                name, 
                description, 
                config,
                max_frame_size
                ) VALUES (%s, %s, %s, %s)
        '''
        try:            
            self.cur.executemany(sql, values) 
            self.conn.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            self.cur.close()
            self.conn.close()


    def _extract_data_from_config(self):      
        """
            Function reads data from config file and extracts important information from each configuration interface 
            to fill in list of values, that will be later in process() inserted to configurations table
        """                   
        
        with open(self.config) as config:
            data = yaml.safe_load(config)
            interfaces = data['frinx-uniconfig-topology:configuration']['Cisco-IOS-XE-native:native']['interface']

            for interface, configurations in interfaces.items():
                if self.interfaces_to_process != []:
                    if not any(i.lower() in interface.lower() for i in self.interfaces_to_process):
                        continue

                for configuration in configurations:
                    yield interface, configuration


    def process(self):       
        values = []
        
        for interface, configuration in self._extract_data_from_config():
            interface_data = {
            'name': interface + str(configuration['name']),
            'description': None,
            'config': configuration,
            'max_frame_size': None
            }

            for optional in ('mtu', 'description'):
                if optional in configuration.keys():
                    if optional == 'mtu':                    
                        interface_data['max_frame_size'] = configuration['mtu']
                    else:
                        interface_data[optional] = configuration[optional]

            values.append(
                    (
                    str(interface_data["name"]), 
                    interface_data['description'], 
                    Json(interface_data["config"]), 
                    interface_data["max_frame_size"]
                    )
                )
                
        self._insert_data_list(values)
        self._update_ethernet_port_channel_id()

        if self.conn is not None:
            self.cur.close()
            self.conn.close()

if __name__ == '__main__':
    create_configurations_table()
    InterfaceConfigurationsProcessor('configClear_v2.json', ['ethernet', 'port-channel']).process()