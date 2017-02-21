# VESK
VESK embedded group coursework


# setting up broker server

To set-up broker server mosquitto package needs to be downloaded

sudo apt-get install mosquitto

To start the broker just a simple command line 

mosquitto -c broker_config_file.conf

-c means to read the configuration for the server, if not specified it will run default configuration. Since we implemented that only specific users can access the router the config file obtains all this information

broker_config_file.conf is a name of the configuration file

in configuration file the anonymous mode is disabled to enable only specific users to be able to connect. Then it specifies the file that contains username and passwords, the format is username:password. Password is encrypted.

to include new user with password this command is used

mosquitto_passwd -b password_file.txt username password

the port needs to be different due to the fact that defualt port 1883 is taken by the python script. This is because python script and this server were running on the same machine


to publish a message from the console one can use following command

mosquitto_pub -u "username" -P "password" -t "topic" -m "message"

this was used to do a different settings



