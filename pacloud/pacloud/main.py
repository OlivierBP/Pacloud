#!/usr/bin/python

import argparse
import libpacloud
import re
import os

def main():
    parser = argparse.ArgumentParser()
    package_group = parser.add_mutually_exclusive_group()
    package_group.add_argument('-s', '--search', help='search for specified package', metavar='package')
    package_group.add_argument('-i', '--install', help='install specified package', metavar='package')
    package_group.add_argument('-r', '--remove', help='remove specified package', metavar='package')
    # package_group.add_argument('-c', '--compile', help='compile specified package', metavar='package')
    package_group.add_argument('-q', '--query', help='return detailed informations regarding specified package', metavar='package')
    parser.add_argument('-u', '--update', help='update local database', action='store_true')
    parser.add_argument('-U', '--upgrade', help='upgrade system', action='store_true')
    # parser.add_argument('--update-config', help='send user configuration to the server', action='store_true')

    args = parser.parse_args()
    args_dict = dict((k,v) for k,v in args.__dict__.items() if v is not None and v is not False)
    for (name, arg) in args_dict.items():
        if name == "search":
            search(arg)
        elif name == "update":
            update()
        elif name == "install":
            install(arg)
        elif name == "remove":
            remove(arg)
        elif name == "query":
            query(arg)
        elif name == "upgrade":
            upgrade()
        else:
            func = getattr(libpacloud, name)
            if (arg):
                print(func(arg))
            else:
                func()

def search(arg):
    results = libpacloud.search(arg)
    if not results:
        print("No result found for search key: {}".format(arg))
        return
    print("Results for search key: {}".format(arg))
    for package in results:
        firstline = "\n\033[1m{}\033[0;36m (".format(package['name'])
        for version in package['versions']:
            firstline += " {} ".format(version['number'])
        firstline += ")\033[0m "
        try:
            firstline += "\033[32m[installed: {}]\033[0m".format(package['installed'])
        except KeyError:
            pass
        print(firstline)
        print("\t"+package["description"])

def update():
    print('Update...')
    libpacloud.update()
    print('Done!')

def _ambiguous_search(list):
    print("Error: ambiguous package search")
    print("Found packages:")
    for package in list:
        print(package["name"])

def _check_unique_package(arg):
    packages = libpacloud.search(arg)
    if(len(packages) != 1):
        if(arg not in libpacloud.list_packages()):
            _ambiguous_search(packages)
            return False
    return True

def install(arg):
    version = None
    version_check = re.search('-[0-9]', arg)
    if(version_check != None):
        pos = version_check.start()
        version = arg[pos+1:]
        arg = arg[:pos:]
    if not _check_unique_package(arg):
        return
    else:
        packages = libpacloud.search(arg)
        arg = packages[0]["name"]
    print("Resolving dependencies...\n")
    dependencies_list = libpacloud.list_dependencies(arg, version)
    if(len(dependencies_list) == 0):
        print("No package found. Aborting.")
        return False
    strdep = "Packages ({}):".format(len(dependencies_list))
    for dependency, version in dependencies_list:
        strdep += " {}-{} ".format(dependency, version)
    print(strdep +"\n")
    if(_yesno("Do you want to proceed with installation? [Y/n] ")):
        print("Installing packages...")
        for package, version in dependencies_list:
            try:
                print(package + "... ")
                total_files = next(libpacloud.install(package, version))
                for i in libpacloud.install(package, version):
                    _print_progress_bar(int(i/total_files*100))
            except PermissionError:
                print("Permission denied")
                return
        print("Done!")

def _print_progress_bar(percentage):
    ts = os.get_terminal_size()
    bar = "\033[1F\033[{}C".format(ts.columns - 52) # Putting cursor at the right position
    bar = "{}[{}{}]".format(bar, '='*(int(percentage/2)), '-'*(int(50-percentage/2)))
    print(bar)

def remove(arg):
    if not _check_unique_package(arg):
        return
    else:
        arg = libpacloud.search(arg)[0]["name"]
    print('Resolving dependencies...\n')
    dependencies_list = libpacloud.list_remove_dependencies(arg)
    if(len(dependencies_list) == 0):
        print("No package found. Aborting.")
        return False
    strdep = "Packages ({}):".format(len(dependencies_list))
    for dependency in dependencies_list:
        strdep += " {} ".format(dependency)
    print(strdep +"\n")
    if(_yesno("Do you want to remove these packages? [Y/n] ")):
        for package in dependencies_list:
            try:
                print(package + "... ")
                total_files = next(libpacloud.remove(package))
                for i in libpacloud.remove(package):
                    _print_progress_bar(int(i/total_files*100))
            except PermissionError:
                print("Error: permission denied")
                return
        print("Done!")

def upgrade():
    print('Resolving dependencies...\n')
    dependencies_list = libpacloud.upgrade()
    if(len(dependencies_list) == 0):
        print("No package found. Aborting.")
        return False
    strdep = "Packages ({}):".format(len(dependencies_list))
    for dependency, version in dependencies_list:
        strdep += " {}-{} ".format(dependency, version)
    print(strdep +"\n")
    if(_yesno("Do you want to update these packages? [Y/n] ")):
        print("Installing packages...")
        for package, version in dependencies_list:
            try:
                print(package + "... ")
                total_files = next(libpacloud.install(package, version))
                for i in libpacloud.install(package, version):
                    _print_progress_bar(int(i/total_files*100))
            except PermissionError:
                print("Permission denied")
                return
        print("Done!")

def query(arg):
    results = libpacloud.search(arg)
    if(len(results) != 1):
        _ambiguous_search(results)
        return
    print('Name        : {}'.format(results[0]['name']))
    print('Description : {}'.format(results[0]['description']))
    print('Versions    :')
    for version in results[0]['versions']:
        print('  - Number  : {}'.format(version['number']))
        print('    Dependencies:', end="")
        for dep in version['dependencies']:
            print(' {} '.format(dep), end="")
        print()
    try:
        print('Installed   : {}'.format(results[0]['installed']))
    except KeyError:
        pass
    try:
        results[0]['required_by']
        print('Required by :', end="")
        for req in results[0]['required_by']:
            print(' {} '.format(req), end="")
        print()
    except KeyError:
        pass

def _yesno(message):
    if(os.geteuid() != 0):
        print("Insufficient privileges. Try running the command with sudo.")
        return False
    user_choice = input(message)
    return user_choice in ['', 'Y', 'y']

