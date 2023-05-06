#### Python File ####
import paramiko
import time
from netaddr import IPAddress # pylint: disable=import-error
from common_functions import vault_liason

vault_creds = vault_liason.get_creds() # Get all creds in our Vault
print(vault_creds)

## Get OpenGear Default Creds ##
opengear_username = vault_creds['opengear_default_creds']['username']
opengear_password = vault_creds['opengear_default_creds']['password']

## Get Network Local Accounts ##
admin_password = vault_creds['bne_network_local_accounts']['admin_password']
bcadmin_password = vault_creds['bne_network_local_accounts']['badmin_password']
nbcuadmin_password = vault_creds['bne_network_local_accounts']['cuadmin_password']


def ncs540_ssh_config(router_hostname, management_ip, management_subnet ,management_gw, opengear_ip, opengear_serial_port):
    try:
        # Set the hostname and port number of the OpenGear device
        hostname = opengear_ip
        port = 22 # The default SSH port for OpenGear is 22, but this may vary depending on your setup

        # Create an SSH client object using Paramiko
        client = paramiko.SSHClient()

        # Automatically add the OpenGear device's SSH key to the client's known_hosts file
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the OpenGear device
        client.connect(hostname, port=port, username=opengear_username, password=opengear_username)

        # Open a channel to send commands to the device
        channel = client.invoke_shell()

        # Wait for the command prompt to appear
        time.sleep(1)
        output = channel.recv(1000).decode('utf-8')
        channel.send("pmshell" + '\n')
        time.sleep(1)
        output = channel.recv(1000).decode('utf-8')
        channel.send(f'{opengear_serial_port}'+'\n')
        time.sleep(1)
        output = channel.recv(1000).decode('utf-8')
        if 'ERROR' in output:
            return "Serial Port Unreachable - Verify Physical Connection to Console"
        else:
            channel.send( '\n')
            output = channel.recv(1000).decode('utf-8')
            while '#' not in output:
                output = channel.recv(1000).decode('utf-8')
                if "Enter root-system username:" in output:
                    channel.send("nbcuadmin" + '\n')
                elif "Enter secret:" in output:
                    channel.send(f"{cuadmin_password}" + '\n')
                elif "Enter secret again:" in output:
                    channel.send(f"{cuadmin_password}" + '\n')
                elif 'Username:' in output:
                    # Send the username
                    channel.send("nbcuadmin" + '\n')
                elif 'Password:' in output:
                    # Send the password
                    channel.send(f"{cuadmin_password}"+ '\n')
                time.sleep(2)
            ###
            # You are now logged in and can send commands to the device using the channel object
            # For example, send the "show version" command and print the output
            config_list =[
                    'term len 0',
                    'term width 0',
                    'conf t',
                    f'username admin secret {admin_password}',
                    'username admin group root-lr',
                    'username admin group cisco-support',
                    f'username bcadmin secret {badmin_password}',
                    'username bcadmin group root-lr',
                    'username bcadmin group cisco-support',
                    'username nbcuadmin group root-lr',
                    'username nbcuadmin group netadmin',
                    'username nbcuadmin group cisco-support',
                    f'username nbcuadmin secret {cuadmin_password}',
                    f'hostname {router_hostname}',
                    f'''banner motd @           
                        the banner stuff
                        This equipment is for authorized use only.  Unauthorized use of this 
                        equipment is prohibited by law.   All usage is monitored and logged. 
                        {router_hostname} managed by BC TACACS v1.0            @''',
                    'clock timezone UTC UTC',
                    'service timestamps log datetime localtime show-timezone',
                    'service timestamps debug datetime localtime msec show-timezone',

                    #### VRF Management ####
                    'vrf management',
                    'description *** Network Management ***',
                    'address-family ipv4 unicast',        
                    'tpa',
                    'vrf management',
                    'address-family ipv4',
                    'update-source dataports MgmtEth0/RP0/CPU0/0',
                    #### Interfaces: Management ####
                    'interface MgmtEth0/RP0/CPU0/0',
                    'vrf management',
                    f'ipv4 address {management_ip} {management_subnet}',
                    'no shutdown',
                    #### Routing: Static-Management ####
                    'router static',
                    'vrf management',
                    'address-family ipv4 unicast',
                    f'0.0.0.0/0 MgmtEth0/RP0/CPU0/0 {management_gw}',
                    #### ACL NBCU-VTY-ACCESS ####
                    'ipv4 access-list nbcu-vty-access',
                    '10 remark subnets_allowed_for_remote_access',
                    '20 permit ipv4 x.x.x.x/11 any',
                    '200 deny ipv4 any any log',
                    ### DOMAIN ###
                    'domain name inbcu.com',
                    'domain vrf management name x.com',
                    'domain vrf management name-server x.x.x.x',
                    'domain vrf management lookup source-interface MgmtEth0/RSP0/CPU0/0',
                    #### SSH SERVER ####
                    'ssh server dscp 16',
                    'ssh server logging',
                    'ssh timeout 60',
                    'ssh server capability netconf-xml',
                    'ssh server v2',
                    'ssh server vrf management ipv4 access-list nbcu-vty-access',
                    'ssh server netconf vrf management',
                    #### Line VTY ####
                    'line template vty-nbcu-mgmt',
                    'exec-timeout 30 0',
                    'length 23',
                    'transport input ssh',
                    'vty-pool default 0 16 line-template vty-nbcu-mgmt',
                    'commit',
                    'end',
            ]
            for config in config_list:
                channel.send(config + '\n')
                time.sleep(.5)
                output = channel.recv(1000).decode('utf-8')

            time.sleep(5)
            channel.send("show run" + '\n')
            time.sleep(5)
            output = channel.recv(9000).decode('utf-8')

            # Close the SSH connection
            client.close()
            #return output
            return output
        
    except Exception as error: # pylint: disable=broad-exception-caught
        return error

def nexus9300_ssh_config(router_hostname, management_ip, management_subnet ,management_gw, opengear_ip, opengear_serial_port):
    try:
        #Convert Management Subnet To CIDR
        management_cidr = IPAddress(management_subnet).netmask_bits()
        
        # Set the hostname and port number of the OpenGear device
        hostname = opengear_ip
        port = 22 # The default SSH port for OpenGear is 22, but this may vary depending on your setup

        # Create an SSH client object using Paramiko
        client = paramiko.SSHClient()

        # Automatically add the OpenGear device's SSH key to the client's known_hosts file
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the OpenGear device
        client.connect(hostname, port=port, username=opengear_username, password=opengear_password)

        # Open a channel to send commands to the device
        channel = client.invoke_shell()

        # Wait for the command prompt to appear
        time.sleep(1)
        output = channel.recv(1000).decode('utf-8')
        channel.send("pmshell" + '\n')
        time.sleep(1)
        output = channel.recv(1000).decode('utf-8')
        channel.send(f'{opengear_serial_port}'+'\n')
        time.sleep(1)
        output = channel.recv(1000).decode('utf-8')
        if 'ERROR' in output:
            return "Serial Port Unreachable - Verify Physical Connection to Console"
        else:
            channel.send( '\n')
            output = channel.recv(1000).decode('utf-8')
            while f'{router_hostname}#' not in output:
                print("Inside While Loop")
                output = channel.recv(1000).decode('utf-8')
                if "Abort Power On Auto Provisioning" in output:
                    channel.send("yes" + '\n')
                    time.sleep(30)
                elif "enforce password standard:" in output:
                    channel.send("y" + '\n')
                elif "login:" in output:
                    channel.send("admin" + '\n')
                elif "Password:" in output:
                    channel.send(f"{admin_password}" + '\n')
                    time.sleep(2)
                elif 'password for "admin":' in output:
                    channel.send(f"{admin_password}" + '\n')
                elif "Would you like to enter the basic configuration dialog (yes/no):" in output:
                    channel.send("yes" + '\n')
                elif "Do you want to enforce secure password standard (yes/no)" in output:
                    channel.send("y" + '\n')
                elif "[n]" in output:
                    channel.send("n" + '\n')   
                elif "Enter the switch name" in output:
                    channel.send(f"{ router_hostname }" + '\n')  
                elif "Continue with Out-of-band (mgmt0) management configuration" in output:
                    channel.send("n" + '\n')
                elif "Enable the ssh service?" in output:
                    channel.send("n" + '\n') 
                elif "(L3/L2)" in output:
                    channel.send("L3" + '\n')
                elif "(shut/noshut)" in output:
                    channel.send("shut" + '\n')
                elif "(strict/moderate/lenient/dense)" in output:
                    channel.send("strict" + '\n')
                elif "Use this configuration and save it?" in output:
                    channel.send("y" + '\n')
                    time.sleep(30)

            ###t
            # You are now logged in and can send commands to the device using the channel object
            # For example, send the "show version" command and print the output
            config_list =[
                    'term len 0',
                    'term width 511',
                    'conf t',
                    f'hostname {router_hostname}',
                    f'username admin password {admin_password} role network-admin',
                    f'username cuadmin password {cuadmin_password} role network-admin',
                    f'username bcadmin password {bcadmin_password} role network-admin',
                    'feature ssh',
                    'vrf context management',
                    'ip domain-name inbcu.com',
                    'ip name-server 100.x.x.135 100.x.x.50 x.x.x.x.61',
                    f'ip route 0.0.0.0/0 {management_gw}',
                    'interface mgmt0',
                    'vrf member management',
                    f'ip address {management_ip}/{management_cidr}',
                    'no shut'
                    'end',
                    'copy run start',
            ]
            time.sleep(1)
            for config in config_list:
                channel.send(config + '\n')
                time.sleep(1)
                output = channel.recv(150).decode('utf-8')
            time.sleep(5)
            channel.send("show run" + '\n')
            time.sleep(5)
            output = channel.recv(9000).decode('utf-8')
            channel.send("end" + '\n')

            # Close the SSH connection
            client.close()
            #return output
            print("Complete")
            return output
        
    except Exception as error: # pylint: disable=broad-exception-caught
        return error
		
		
		
		
####  AT FLASK SIDE (FRONT-END) ###

@app.route('/', methods=['GET', 'POST'])
def index():
    output = ''
    if request.method == 'POST':
        hostname = request.form['hostname']
        management_ip = request.form['management_ip']
        management_subnet = request.form['management_subnet']
        management_gw = request.form['management_gw']
        opengear_ip = request.form['opengear_ip']
        serial_port = request.form['serial_port']
        device_model = request.form['device_model']
        print (device_model)  
        
        if device_model == "NCS 540":
            output = ncs540_ssh_config(router_hostname=hostname,
                                      management_ip=management_ip,
                                      management_subnet=management_subnet,
                                      management_gw=management_gw,
                                      opengear_ip=opengear_ip,
                                      opengear_serial_port=serial_port)
            
        elif device_model == "NEXUS 9300":
            output = nexus9300_ssh_config(router_hostname=hostname,
                                      management_ip=management_ip,
                                      management_subnet=management_subnet,
                                      management_gw=management_gw,
                                      opengear_ip=opengear_ip,
                                      opengear_serial_port=serial_port)
        else:
            output="Model Not Supported"

    return render_template('index.html', output=output)
