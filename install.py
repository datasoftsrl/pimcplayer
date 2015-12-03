#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This is part of PiMCPlayer.
#
# Copyright (C) 2015 DataSoft Srl
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import os, sys, string, json, random
from os import path
from contextlib import closing

import paramiko as pm
import scpclient
from getpass import getpass

################################################################################
# METADATA                                                                     #
################################################################################
VERSION = '1.1.0'
################################################################################
################################################################################

LOCATION = path.dirname(sys.argv[0])
SAVEFILE = path.join(LOCATION, 'save.json')
USERNAME = 'pi'
PASSWORD = 'raspberry'

# already used random strings
rand_used = set()
# queue for menu printing
menu = []
# information dict
info = None

def error(string):
  '''
  Print an error string like:
  '[!] message'
  
  < string: error message
  '''
  print('[!] {}'.format(string), file=sys.stderr)

def note(string):
  '''
  Print a warning string like:
  '[*] message'
  
  < string: error message
  '''
  print('[*] {}'.format(string))

def rand_name():
  '''
  Returns a random 8 alphabetic characters string.
  
  > rand: random string 
  '''
  while True:
    rand = ''.join(random.choice(string.ascii_letters) for i in range(8))
    if rand not in rand_used:
      rand_used.add(rand)
      break
  
  return rand

def question(message, type_='str', check=lambda e: True, password=False):
  '''
  Prints a question and continues to ask until input is correct.
  
  < message: string to print for asking
  < type_: type of input (int, str, ...)
  < check: function to check input validity
  
  > sel: valid input
  '''
  # transform string class in class object
  etype = eval(type_)
  
  sel = None
  while True:
    # if it's not the first time asking
    if sel is not None:
      error('Input provided is not valid. Please, retry.')
    try:
      if password:
        sel = etype(getpass('[?] {} '.format(message)))
      else:
        sel = etype(input('[?] {} '.format(message)))
      if check(sel):
        break
    except ValueError:
      sel = True
      pass
  
  return sel
      
def print_menu():
  '''
  Prints menu option, waiting for user selection, and reasking question if
  inserted data is not valid.
  '''
  count = 1
  for entry in menu:
    print('{}) {}'.format(count, entry))
    count += 1
  print('q) Quit\n')
  
  while True:
    sel = input('Select a number from the above: ')
    if sel == 'q':
      sys.exit(0)
    try:
      number = int(sel)
      if number >= 0 and number <= len(menu):
        break
    except ValueError:
      pass
  
  return number

def clean_up(message=False):
  '''
  Clean previously generated config files, plus save file.
  
  < message: notify to user of deleted files.
  '''
  config = path.join(LOCATION, 'config')
  for file in os.listdir(config):
    if file.startswith('pi'):
      filepath = path.join(config, file)
      os.remove(filepath)
      if message:
        note('{} removed.'.format(filepath))
  filepath = path.join(LOCATION, 'save.json')
  if path.isfile(filepath):
    os.remove(filepath)

def gen_config():
  # clean up before starting
  clean_up()
  
  # init dict information
  info = {}
  
  # begin to gather information from user
  wallpath = path.join(LOCATION, 'config', 'piwall')
  with open(wallpath, 'w') as wall:
    info['wall'] = rand_name()
    info['wall_x'] = 0
    info['wall_y'] = 0
    tmp_arr = question(
      'Videowall arrangement? (ex. 2x2)',
      check=lambda e: 'x' in e and len(e) > 2
    )
    # split arrangement at x moltiplication sign
    tmp_col, tmp_row = tmp_arr.split('x')
    info['arr_col'] = int(tmp_col)
    info['arr_row'] = int(tmp_row)
    info['tot_monitor'] = info['arr_col'] * info['arr_row']
    info['width'] = question(
      'Single monitor width?',
      type_='int',
      check=lambda e: e > 0
    )
    info['height'] = question(
      'Single monitor height?',
      type_='int',
      check=lambda e: e > 0
    )
    # wall size is monitor size for number of monitors
    info['wall_width'] = info['width'] * info['arr_col']
    info['wall_height'] = info['height'] * info['arr_row']
    
    # write wall config to file
    wall.write('[{}]\n'.format(info['wall']))
    wall.write('x={}\n'.format(info['wall_x']))
    wall.write('y={}\n'.format(info['wall_y']))
    wall.write('width={}\n'.format(info['wall_width']))
    wall.write('height={}\n'.format(info['wall_height']))
    wall.write('\n')
    
    info['mm_width'] = question(
      'Single monitor inside width? (in millimeters)',
      type_='int',
      check=lambda e: e > 0
    )
    mm_bezel = question(
      'Single monitor bezel width? (in millimeters)',
      type_='int',
      check=lambda e: e > -1
    )
# formula: bezel in pixel is equal to 1 px/mm for bezel in millimeters
    # 1 px/mm is calculated with monitor width in pixel divided by monitor
    # width in millimeters.
    info['bezel'] = round(info['width'] / info['mm_width'] * mm_bezel)

    # wall size is monitor size for number of monitors
    info['wall_width'] = (info['width'] * info['arr_col']) + \
        2 * info['bezel']
    info['wall_height'] = (info['height'] * info['arr_row']) + \
        2 * info['bezel']
    
    # write wall config to file
    wall.write('[{}]\n'.format(info['wall']))
    wall.write('x={}\n'.format(info['wall_x']))
    wall.write('y={}\n'.format(info['wall_y']))
    wall.write('width={}\n'.format(info['wall_width']))
    wall.write('height={}\n'.format(info['wall_height']))
    wall.write('\n')
    
    info['monitors'] = []
    count = 1
    for i in range(info['arr_row']):
      x = 0 if i == 0 else (i * info['width']) + 2*info['bezel']
      for k in range(info['arr_col']):
        y = 0 if k == 0 else (k * info['height']) + 2*info['bezel']
        monitor = {
          'id': count,
          'name': rand_name(),
          'width': info['width'],
          'height': info['height'],
          'x': x,
          'y': y
        }
        info['monitors'].append(monitor)
        count += 1
    
    # write tile config and pitile files
    for mon in info['monitors']:
      wall.write('[{}]\n'.format(mon['name']))
      wall.write('wall={}\n'.format(info['wall']))
      wall.write('x={}\n'.format(mon['x']))
      wall.write('y={}\n'.format(mon['y']))
      wall.write('width={}\n'.format(mon['width']))
      wall.write('height={}\n'.format(mon['height']))
      wall.write('\n')
      
      tilepath = path.join(LOCATION, 'config', 'pitile'+str(mon['id']))
      with open(tilepath, 'w') as tile:
        tile.write('[tile]\n')
        tile.write('id=pi{}\n'.format(mon['id']))
    
    # write final section of tile config
    wall.write('[pimcplayer]\n')
    for mon in info['monitors']:
      wall.write('pi{}={}\n'.format(mon['id'], mon['name']))
    
    # save info into a json file
    with open(SAVEFILE, 'w') as js:
      json.dump(info, js, indent=4)

def _fixed_scp_read_response(channel):
  '''
  Corrects library method in evaluating response byte.
  
  < channel: channel to init scp communication
  '''
  scpclient.msg = scpclient._scp_recv(channel, scpclient._MISC_BUF_LEN)

  if not scpclient.msg:
    raise scpclient.SCPError('Empty response')

  if scpclient.msg[0] == 0:
    # Normal result.
    return
  elif scpclient.msg[0] == 1:
    raise scpclient.SCPError('Server error: {0!r}'.format(
      scpclient.msg[1:]))
  else:
    raise scpclient.SCPError('Invalid response: {0!r}'.format(
      scpclient.msg))

def ssh_connect(hostname, username, password):
  '''
  Create a ssh connection to host, with username and password given.
  
  < hostname: string host or ip to connect
  < username: username for connection
  < password: password for connection
  
  > ssh: paramiko ssh connection object
  '''
  ssh = pm.SSHClient()
  ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
  ssh.connect(hostname=hostname, username=username, password=password)
  
  return ssh

def ssh_command(command, ssh, password, root=False, no_out=False):
  '''
  Launch a command from ssh client.

  < command: string command to execute
  < ssh: paramiko ssh client already connected
  < password: optional overwrite password
  < root: flag, true if command is to execute as root
  < no_out: suppress output
  '''
  # force sudo to ask password and take it from stdin
  if root:
    command = 'sudo -k -S {}'.format(command)

  stdin, stdout, stderr = ssh.exec_command(command)
  if root:
    # give the password
    stdin.write('{}\n'.format(password))
    stdin.flush()
  if not no_out:
    for line in stdout:
      print(line, end='')

def ssh_file(filename, ssh, out_name=None, permissions='0644'):
  '''
  Send file to host marked by ssh connection.
  
  < filename: path of file to send
  < ssh: paramiko ssh connection object
  < out_name: name to give to sent file
  < permission: octal representation of permissions
  '''
  if not out_name:
    out_name = path.basename(filename)
  with closing(scpclient.Write(ssh.get_transport(), '.')) as scp:
    scp.send_file(filename, override_mode=permissions, remote_filename=out_name)

def upload_all():
  '''
  Upload configuration (.piwall, .pitile) to the tiles.
  '''
  # if not step 1 do not execute step 2
  if not path.isfile(SAVEFILE):
    error('Generate config before uploading it!')
    return
  
  # if info informations aren't already loaded, load them from json file
  global info
  if not info:
    with open(SAVEFILE, 'r') as js:
      info = json.load(js)
  
  # inject code into library
  scpclient._scp_read_response = _fixed_scp_read_response
  
  piwall = path.join(LOCATION, 'config', 'piwall')
  pitile = path.join(LOCATION, 'config', 'pitile')
  pwomxp_serv = path.join(LOCATION, 'scripts', 'pwomxplayer')
  pwomxp_conf = path.join(LOCATION, 'config', 'pwomxplayer')
  for dev in sorted(info['monitors'], key=lambda x: x['id']):
    # gather hostname and eventual password for the tile
    print('Tile {}:'.format(dev['id']))
    hostname = question(
      'Hostname or address?',
      check=lambda e: len(e) > 0
    )
    user = question(
      'Username? (default "{}")'.format(USERNAME)
    )
    if len(user) == 0: user = USERNAME
    password = question(
      'Password for user "{}"? (default "{}")'.format(user, PASSWORD),
      password=True
    )
    if len(password) == 0: password = PASSWORD
    
    # upload piwall and pitile files
    ssh = ssh_connect(hostname, user, password)
    ssh_file(piwall, ssh, '.piwall')
    ssh_file('{}{}'.format(pitile, dev['id']), ssh, out_name='.pitile')
    
    # upload service files
    ssh_file(pwomxp_conf, ssh, out_name="pwomxplayer.conf", permissions='0755')
    ssh_command('mv pwomxplayer.conf /etc/default/pwomxplayer', ssh, password,
        True, True)
    ssh_file(pwomxp_serv, ssh, out_name="pwomxplayer.serv", permissions='0755')
    ssh_command('mv pwomxplayer.serv /etc/init.d/pwomxplayer', ssh, password,
        True, True)
    ssh_command('update-rc.d pwomxplayer defaults', ssh, password, True, True)
    ssh_command('/etc/init.d/pwomxplayer start', ssh, password, True, True)

def main():
  while True:
    if len(menu) == 0:
      menu.append('Generate configuration files')
      menu.append('Install configuration and player service')
      menu.append('Clean created configuration files')
    else:
      print()

    number = print_menu()

    if number == 1:
      gen_config()
    elif number == 2:
      upload_all()
    elif number == 3:
      clean_up(True)

if __name__ == '__main__':
  main()
