import argparse
import os
import re
from shutil import copyfile
import yaml

manifest_file = 'manifest.yaml'
manifest_version = 1

char_regex = '^core_char_\d*.dat$'
user_regex = '^core_user_\d*.dat$'

install_regex = '.*_ccp_.*'
config_regex = '^(?!cache).*$'


def main(args):

    settings = load_settings()

    if args.force:
        settings['touched_files'] = []
    
    if args.char:
        settings['touched_files'] += sync_chars(settings)

    if args.user:
        settings['touched_files'] += sync_users(settings)

    with open(manifest_file, 'w') as stream:
        yaml.dump(settings, stream, default_flow_style = False)


def sync_chars(settings):

    default_char_file = os.path.join(settings['eve_settings_dir'], settings['default_char'])
    char_list = [m.group() for line in os.listdir(eve_settings_dir) for m in [re.search(char_regex, line)] if m]

    touched = []
    
    for char_file in char_list:
        if char_file not in settings['touched_files'] and char_file != settings['default_char']:
            copyfile(default_char_file, os.path.join(settings['eve_settings_dir'], char_file))
            touched.append(char_file)

    print ('Chars synced.')
    return touched


def sync_users(settings):

    default_user_file = os.path.join(settings['eve_settings_dir'], settings['default_user'])
    user_list = [m.group() for line in os.listdir(settings['eve_settings_dir']) for m in [re.search(user_regex, line)] if m]

    touched = []
    
    for user_file in user_list:
        if user_file not in settings['touched_files'] and user_file != settings['default_user']:
            copyfile(default_user_file, os.path.join(settings['eve_settings_dir'], user_file))
            touched.append(user_file)

    print ('Users synced.')
    return touched


def load_settings():

    if not os.path.isfile(manifest_file):
        print('No valid manifest file')
        if not create_default_manifest():
            print('Unable to create default file')

    with open(manifest_file, 'r') as stream:
        try:
            settings = yaml.load(stream)
        except:
            print('Unable to load manifest file')
            exit(1)

    if not settings['version'] == manifest_version:
        if settings['version'] > manifest_version:
            print('Unknown manifest version. Exiting.')
            exit(1)
        print('Older manifest version.  This should still work.  I hope.')
        settings = migrate_manifest(settings)
        
    if not 'default_char' in settings:
        print('No default character. Exiting.')
        exit(1)
        
    if not 'default_user' in settings:
        print('No default user. Exiting.')
        exit(1)

    if not 'eve_config_dir' in settings:
        print('No configuration directory.  Setting default')
        settings['eve_config_dir'] = os.path.join(os.getenv('LOCALAPPDATA'), 'CCP\\EVE')

    settings['eve_install_dir'] = os.path.join(settings['eve_config_dir'], select_eve_install(settings))

    settings['eve_settings_dir'] = os.path.join(settings['eve_install_dir'], select_install_settings(settings))
    
    return settings


def select_eve_install(settings):

    return select_directory_or_file(settings, settings['eve_config_dir'], install_regex, 'eve_install_dir')


def select_install_settings(settings):

    return select_directory_or_file(settings, settings['eve_install_dir'], config_regex, 'eve_settings_dir')


def select_directory_or_file(settings, dir, regex, value):

    # DEBUG
    print('{dir} {regex} {value}'.format(**locals()))

    items = [m.group() for line in os.listdir(dir) for m in [re.search(regex, line)] if m]
    last_value = settings.get(str(value), None)
    last_index = None

    # DEBUG
    print('Last value: {last_value}'.format(**locals()))

    for index, item in enumerate(items):
        print('[{index}] {item}'.format(**locals()))

        if item in last_value:
            last_index = index

    response = input('Select {value}{default_index}: '.format(value = value, default_index=' [{index}]'.format(index=last_index) if last_index is not None else '')) or last_index

    try:
        return items[int(response)]
    except(TypeError, IndexError):
        print('Invalid {value}. Exiting'.format(**locals()))
        exit(1)


def create_default_manifest():

    manifest = {}
    manifest['version'] = manifest_version

    eve_config_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'CCP\\EVE')
    if not os.path.exists(eve_config_dir):
        print('Unable to find eve settings directory :[')
        return False
    manifest['eve_config_dir'] = eve_config_dir

    eve_install_list = [m.group() for line in os.listdir(eve_config_dir) for m in [re.search(install_regex, line)] if m]

    if not len(eve_install_list) > 0:
        print('Unable to find any installs :[')
        return False

    eve_settings_list = [m.group() for line in os.listdir(os.path.join(eve_config_dir, eve_install_list[0])) for m in [re.search(config_regex, line)] if m]

    if not len(eve_settings_list) > 0:
        print('Unable to find any settings :[')
        return False

    eve_settings_files = os.listdir(os.path.join(eve_config_dir, eve_settings_list[0]))
    char_list = [m.group() for line in eve_settings_files for m in [re.search(char_regex, line)] if m]
    user_list = [m.group() for line in eve_settings_files for m in [re.search(user_regex, line)] if m]

    if not len(char_list) > 0:
        print('Unable to find any character files :[')
        return False
    
    if not len(user_list) > 0:
        print ('Unable to find any user files :[')
        return False

    manifest['default_char'] = char_list[0]
    manifest['default_user'] = user_list[0]

    manifest['installs'] = {}

    with open(manifest_file, 'w') as stream:
        yaml.dump(manifest, stream, default_flow_style = False)

    return True

def migrate_manifest(settings):
    if settings['version'] == 0:
        
        # Update to the new version
        settings['version'] = manifest_version

        # Update eve_config_dir
        settings['eve_config_dir'] = os.path.join(os.getenv('LOCALAPPDATA'), 'CCP\\EVE')

        # Setup installs section
        settings['installs'] = {}

        # Move touched files to the install directory
        new_config = {}
        new_config['touched_files'] = settings['touched_files']

        # Copy old defaults over to this install's settings
        new_config['default_char'] = settings['default_char']
        new_config['default_user'] = settings['default_user']

        # Set this section
        settings['installs'][settings['eve_settings_dir']] = new_config

        del(settings['touched_files'])
        del(settings['eve_settings_dir'])


    with open(manifest_file, 'w') as stream:
        yaml.dump(settings, stream, default_flow_style = False)

    return settings

        
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Sync EVE char and user settings files.')
    parser.add_argument('-f', '--force', action='store_true', default=False, help='Overwrite all files.')
    parser.add_argument('-c', '--char', action='store_true', default=False, help='Sync char files.')
    parser.add_argument('-u', '--user', action='store_true', default=False, help='Sync user files.')
        
    args = parser.parse_args()
    main(args)
    
