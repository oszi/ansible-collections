# Oszi's Ansible Collections

Opinionated collections of ansible roles and playbooks for workstations and containers.  
Supported distributions include the latest stable Fedora, Debian, Ubuntu.  
See the collections and role defaults for basic documentation.

### Debian / Ubuntu Login Shells

By default, desktop terminals on Debian are not using login shells. Thus, /etc/profile.d is not sourced.  
Manually enable login shells in desktop terminals. (Profiles / Command)

### RedHat / CentOS Support

Most roles support the latest RedHat family distributions with some tweaking.  
See the [EPEL](https://docs.fedoraproject.org/en-US/epel/) documentation as it is not enabled by default.  
