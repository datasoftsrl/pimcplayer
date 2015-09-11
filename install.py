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

import sys, string, random
from os import path
from collections import deque

import paramiko as pm

################################################################################
# METADATA                                                                     #
################################################################################
VERSION = '1.0.0'
################################################################################
################################################################################

LOCATION = path.dirname(sys.argv[0])

# already used random strings
rand_used = set()
# queue for menu printing
menu = deque()
# information dict
info = { 'monitors': [] }

def rand_name():
  while True:
    rand = ''.join(random.choice(string.ascii_letters) for i in range(8))
    if rand not in rand_used:
      rand_used.add(rand)
      break
  
  return rand

def question(message, type_='str', check=None):
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
      print('Input provided is not valid. Please, retry.', file=sys.stderr)
    try:
      sel = etype(input('[Q] ' + message + ' '))
      if check(sel):
        break
    except ValueError:
      sel = True
      pass
  
  return sel
      
def print_menu():
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

def gen_config():
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
    
    # determine if wall is a vector
    vert_vect = False
    horiz_vect = False
    if info['arr_col'] == 1:
      vert_vect = True
    if info['arr_row'] == 1:
      horiz_vect = True
    count = 1
    for i in range(info['arr_row']):
      y = i * info['height']
      for k in range(info['arr_col']):
        x = k * info['width']
        monitor = {
          'id': count,
          'name': rand_name(),
          'x': x,
          'y': y
        }
        # if 0,0;0,N;N,0;N,N
        if (k == 0 or k == info['arr_col']-1) \
          and (i == 0 or i == info['arr_row']-1):
          if vert_vect:
            monitor['width'] = info['width']
          else:
            monitor['width'] = info['width'] - info['bezel']
          if horiz_vect:
            monitor['height'] = info['height']
          else:
            monitor['height'] = info['height'] - info['bezel']
        # if x,0/N
        elif k == 0 or k == info['arr_col']-1:
          if vert_vect:
            monitor['width'] = info['width']
          else:
            monitor['width'] = info['width'] - info['bezel']
          monitor['height'] = info['height'] - (2 * info['bezel'])
        # if 0/N,x
        elif i == 0 or i == info['arr_row']-1:
          monitor['width'] = info['width'] - (2 * info['bezel'])
          if horiz_vect:
            monitor['height'] = info['height']
          else:
            monitor['height'] = info['height'] - info['bezel']
        # if x,x
        else:
          monitor['width'] = info['width'] - (2 * info['bezel'])
          monitor['height'] = info['height'] - (2 * info['bezel'])
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

def upload_config():
  #ssh = pm.SSHClient()
  #ssh.set_missing_host_key_policy(pm.AutoAddPolicy())
  #ssh.connect('192.168.206.80', username='pi', password='raspberry')
  #
  #with 

def upload_service():
  pass

def main():
  while True:
    if len(menu) != 0:
      print()
    
    menu.append('Generate configuration files')
    menu.append('Install configuration files')
    menu.append('Install player service')

    number = print_menu()

    if number == 1:
      gen_config()
    elif number == 2:
      upload_config()
    else:
      upload_service()

if __name__ == '__main__':
  main()
