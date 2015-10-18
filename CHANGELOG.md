# PiMCPlayer

## 1.0.0
Initial version of software.

## 1.1.0
Added use of paramiko and scpclient for trasmmitting configs and starting
services on the clients. Getpass is used when asking passwords.

Menu has 3 voices, first generates configs, second upload configs and services,
third cleans locally created config.

In ``gen_config``, now config generation works out of the box, with all matrix
setups. A json at the end is written to save changes for next sessions.

In ``upload_all``, informations for every tile are asked, then config and
service files are uploaded.
