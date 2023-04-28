### Network Python Scripts  

Python with Netmiko library for Cisco device configuration and parsing  

#### p2p_config.py  
* lists all p2p /31 interfaces on Cisco router  
* backs up config  


The flow I used is that.

Engineer would provide management info, gw for static route, hostname, opengear IP and serial number  
They select from a dropdown what platform to decide at the back-end based on the platform which method to use and use the variables they entered as arguments  
Paramiko to walk the configuration step by step, prompt by prompts using few logics  
