#!/usr/bin/env python3
import boto3
import sys
from tabulate import tabulate
import subprocess
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

CACHE_FILE_PATH = Path.home() / '.ec2_ssh_cache.json'
CACHE_TTL_SECONDS = 300  # 5 minutes

class KeyManager:
    def __init__(self):
        self.config_file = Path.home() / '.ec2_ssh_config.json'
        self.load_config()

    def load_config(self):
        """Load SSH key mappings from config file."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            self.config = {'instance_keys': {}, 'default_key': ''}

    def save_config(self):
        """Save SSH key mappings to config file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_key_path(self, instance_id):
        """Get SSH key path for an instance."""
        return self.config['instance_keys'].get(instance_id, self.config['default_key'])

    def set_key_path(self, instance_id, key_path):
        """Set SSH key path for an instance."""
        self.config['instance_keys'][instance_id] = key_path
        self.save_config()

    def set_default_key(self, key_path):
        """Set default SSH key path."""
        self.config['default_key'] = key_path
        self.save_config()

    @staticmethod
    def check_ssh_agent():
        """Check if SSH agent is running and return its PID."""
        try:
            return os.environ.get('SSH_AGENT_PID')
        except Exception:
            return None

    @staticmethod
    def add_key_to_agent(key_path):
         """Add key to SSH agent."""
         try:
             # Check if key file exists
             key_path = os.path.expanduser(key_path)  # Handle ~ in paths
             if not os.path.exists(key_path):
                 print(f"Error: Key file {key_path} does not exist")
                 return False

             # Check key file permissions
             key_permissions = oct(os.stat(key_path).st_mode)[-3:]
             if key_permissions not in ['600', '400']:
                 print(f"Warning: Key file {key_path} has incorrect permissions ({key_permissions}). Should be 600 or 400.")
                 fix_perms = input("Would you like to fix the permissions? (y/n): ").lower()
                 if fix_perms == 'y':
                     os.chmod(key_path, 0o600)
                     print("Permissions fixed.")
                 else:
                     return False

             # Try to add the key
             result = subprocess.run(['ssh-add', key_path],
                                     capture_output=True,
                                     text=True,
                                     check=True)

             # Verify the key was added
             verify = subprocess.run(['ssh-add', '-l'],
                                     capture_output=True,
                                     text=True)

             if verify.returncode == 0:
                 print(f"Successfully added key {key_path} to SSH agent")
                 return True
             else:
                 print(f"Failed to verify key addition: {verify.stderr}")
                 return False

         except subprocess.CalledProcessError as e:
             if "Could not open a connection to your authentication agent" in str(e.stderr):
                 print("Error: SSH agent is not running. Please start it with 'eval $(ssh-agent)'")
             else:
                 print(f"Error adding key to SSH agent: {e.stderr}")
             return False
         except Exception as e:
             print(f"Unexpected error: {e}")
             return False

def _format_timedelta(td):
    """Formats a timedelta object into a human-readable string."""
    parts = []
    if td.days > 0:
        parts.append(f"{td.days}d")
    
    seconds = td.seconds
    hours = seconds // 3600
    if hours > 0:
        parts.append(f"{hours}h")
    
    minutes = (seconds % 3600) // 60
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    if not parts or (hours == 0 and minutes == 0): # Show seconds if total is less than a minute or only seconds exist
        parts.append(f"{seconds % 60}s")
        
    return " ".join(parts) if parts else "0s"

def _load_instances_from_cache():
    """Load instances from cache if valid."""
    if CACHE_FILE_PATH.exists():
        try:
            with open(CACHE_FILE_PATH, 'r') as f:
                cache_data = json.load(f)
            
            timestamp_str = cache_data.get('timestamp')
            instances = cache_data.get('instances')

            if timestamp_str and instances is not None:
                cache_timestamp = datetime.fromisoformat(timestamp_str)
                if datetime.now() - cache_timestamp < timedelta(seconds=CACHE_TTL_SECONDS):
                    age = datetime.now() - cache_timestamp
                    print(f"Loaded instances from cache (age: {_format_timedelta(age)}, TTL: {_format_timedelta(timedelta(seconds=CACHE_TTL_SECONDS))}).")
                    return instances
                else:
                    print("Cache expired.")
            else:
                print("Invalid cache file format.")
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Error reading cache file: {e}. Will fetch from AWS.")
    return None

def _save_instances_to_cache(instances):
    """Save instances to cache."""
    cache_data = {
        'timestamp': datetime.now().isoformat(),
        'instances': instances
    }
    try:
        with open(CACHE_FILE_PATH, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print("Instance list cached.")
    except IOError as e:
        print(f"Error writing to cache file: {e}")

def fetch_instances_from_aws():
    """Retrieve all EC2 instances across all regions from AWS."""
    ec2_client = boto3.client('ec2')

    # Get list of all regions
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]

    instances = []
    for region in regions:
        ec2 = boto3.resource('ec2', region_name=region)

        # Get instances in this region
        for instance in ec2.instances.all():
            name = ''
            for tag in instance.tags or []:
                if tag['Key'] == 'Name':
                    name = tag['Value']
                    break

            instances.append({
                'id': instance.id,
                'name': name,
                'type': instance.instance_type,
                'state': instance.state['Name'],
                'public_ip': instance.public_ip_address,
                'private_ip': instance.private_ip_address,
                'region': region,
                'key_name': instance.key_name
            })

    return instances

def get_instances_with_cache_logic(force_refresh=False):
    """Retrieve instances, using cache if available and valid, unless force_refresh is True."""
    if not force_refresh:
        cached_instances = _load_instances_from_cache()
        if cached_instances is not None:
            return cached_instances

    print("Fetching EC2 instances from AWS...")
    instances = fetch_instances_from_aws()
    _save_instances_to_cache(instances)
    return instances

def display_instances(instances):
    """Display instances in a formatted table."""
    if not instances:
        print("No instances found to display.") # Modified message for clarity with filtering
        return

    # Prepare table data
    headers = ['Index', 'Name', 'ID', 'Type', 'State', 'Public IP', 'Private IP', 'Region', 'Key Name']
    table_data = []

    for idx, instance in enumerate(instances, 1):
        table_data.append([
            idx,
            instance['name'],
            instance['id'],
            instance['type'],
            instance['state'],
            instance['public_ip'] or 'N/A',
            instance['private_ip'] or 'N/A',
            instance['region'],
            instance['key_name'] or 'N/A'
        ])

    print(tabulate(table_data, headers=headers, tablefmt='grid'))

def ssh_to_instance(instance, username='ec2-user', key_manager=None):
    """SSH into the selected instance."""
    if not instance['public_ip']:
        print("Error: Instance has no public IP address")
        return

    print(f"\nConnecting to {instance['name']} ({instance['id']}) at {instance['public_ip']}...")

    # Get key path for this instance
    key_path = key_manager.get_key_path(instance['id']) if key_manager else None

    # If no key is configured, prompt for one
    if not key_path:
        print(f"No SSH key configured for instance {instance['id']}")
        key_path = input("Enter path to SSH key file: ").strip()
        if key_path:
            save = input("Save this key for this instance? (y/n): ").lower()
            if save == 'y':
                key_manager.set_key_path(instance['id'], key_path)

            default = input("Set as default key for all instances? (y/n): ").lower()
            if default == 'y':
                key_manager.set_default_key(key_path)

    try:
        ssh_command = ['ssh']

        # Check if SSH agent is running
        if KeyManager.check_ssh_agent():
            if key_path and KeyManager.add_key_to_agent(key_path):
                print("Using SSH agent for authentication")
        elif key_path:
            # If no SSH agent, fall back to direct key specification
            ssh_command.extend(['-i', key_path])

        ssh_command.append(f'{username}@{instance["public_ip"]}')

        subprocess.run(ssh_command)
    except KeyboardInterrupt:
        print("\nConnection terminated by user")
    except Exception as e:
        print(f"Error connecting: {e}")

def manage_keys(key_manager, instances):
    """Manage SSH keys for instances."""
    while True:
        print("\nKey Management:")
        print("1. Set default key")
        print("2. Set key for specific instance")
        print("3. View current key mappings")
        print("4. Add key to SSH agent")
        print("5. List keys in SSH agent")
        print("6. Return to main menu")

        choice = input("\nEnter choice (1-6): ")

        if choice == '1':
            key_path = input("Enter path to default SSH key file: ").strip()
            if key_path:
                key_manager.set_default_key(key_path)
                print("Default key updated")
                if KeyManager.check_ssh_agent():
                    add = input("Add key to SSH agent? (y/n): ").lower()
                    if add == 'y':
                        KeyManager.add_key_to_agent(key_path)

        elif choice == '2':
            if not instances:
                print("No instances available to set a key for.")
                continue
            display_instances(instances) # Display all instances passed for selection
            idx_str = input("\nEnter instance index: ")
            if not idx_str.isdigit():
                print("Invalid index format.")
                continue
            idx = int(idx_str)
            if 1 <= idx <= len(instances):
                instance = instances[idx-1]
                key_path = input("Enter path to SSH key file: ").strip()
                if key_path:
                    key_manager.set_key_path(instance['id'], key_path)
                    print("Instance key updated")
                    if KeyManager.check_ssh_agent():
                        add = input("Add key to SSH agent? (y/n): ").lower()
                        if add == 'y':
                            KeyManager.add_key_to_agent(key_path)
            else:
                print("Invalid index")

        elif choice == '3':
            print("\nCurrent Key Mappings:")
            print(f"Default key: {key_manager.config['default_key']}")
            print("\nInstance-specific keys:")
            for instance_id, key_path in key_manager.config['instance_keys'].items():
                print(f"Instance {instance_id}: {key_path}")

        elif choice == '4':
            if not KeyManager.check_ssh_agent():
                print("SSH agent is not running. Please start it first with 'eval $(ssh-agent)'")
                continue

            key_path = input("Enter path to SSH key file: ").strip()
            if key_path:
                KeyManager.add_key_to_agent(key_path)

        elif choice == '5':
            if not KeyManager.check_ssh_agent():
                print("SSH agent is not running. Please start it first with 'eval $(ssh-agent)'")
                continue

            subprocess.run(['ssh-add', '-l'])

        elif choice == '6':
            break

def filter_instances(instances, name_search=None, type_search=None):
    """Filter instances by name and/or type."""
    filtered_list = list(instances) # Start with a copy

    if name_search:
        name_search_lower = name_search.lower()
        filtered_list = [
            inst for inst in filtered_list
            if name_search_lower in inst['name'].lower()
        ]

    if type_search:
        type_search_lower = type_search.lower()
        filtered_list = [
            inst for inst in filtered_list
            if type_search_lower in inst['type'].lower()
        ]
    return filtered_list

def main():
    try:
        key_manager = KeyManager()

        # Check SSH agent status at startup
        if not KeyManager.check_ssh_agent():
            print("\nNotice: SSH agent is not running. To use SSH agent features, start it with:")
            print("eval $(ssh-agent)")

        all_instances = []
        current_display_instances = []
        is_filtered = False

        all_instances = get_instances_with_cache_logic()
        current_display_instances = all_instances

        while True:
            display_instances(current_display_instances)

            if not all_instances: # No instances found on the account at all
                print("No instances found on your AWS account.")
                action = input("R)efresh, Q)uit? ").lower()
                if action == 'r':
                    all_instances = get_instances_with_cache_logic(force_refresh=True)
                    current_display_instances = all_instances
                    is_filtered = False
                    continue
                else:
                    break
            elif not current_display_instances and is_filtered: # No instances match filter, but some exist
                 print("No instances match your current filter criteria.")


            print("\nOptions:")
            print("1. Connect to instance")
            print("2. Manage SSH keys")
            print("3. Search/Filter instances")
            
            option_number_dynamic = 4
            if is_filtered:
                print(f"{option_number_dynamic}. Reset filter & Refresh instances")
            else:
                print(f"{option_number_dynamic}. Refresh instances")
            
            option_number_quit = option_number_dynamic + 1
            print(f"{option_number_quit}. Quit")

            choice = input(f"\nEnter choice (1-{option_number_quit}): ")

            if choice == '1': # Connect
                if not current_display_instances:
                    print("No instances to connect to. Try changing filter or refreshing.")
                    continue
                idx_str = input("Enter instance index: ")
                if not idx_str.isdigit():
                    print("Invalid index format.")
                    continue
                idx = int(idx_str)

                if 1 <= idx <= len(current_display_instances):
                    username = input("Enter username (default: ec2-user): ").strip() or 'ec2-user'
                    ssh_to_instance(current_display_instances[idx-1], username, key_manager)
                else:
                    print("Invalid index")

            elif choice == '2': # Manage Keys
                manage_keys(key_manager, all_instances) # Pass all_instances

            elif choice == '3': # Search/Filter
                name_search = input("Enter name to search (leave blank for no filter): ").strip()
                type_search = input("Enter type to search (leave blank for no filter): ").strip()
                
                current_display_instances = filter_instances(all_instances, name_search, type_search)
                is_filtered = bool(name_search or type_search)
                if not current_display_instances and is_filtered:
                    # Message will be displayed by display_instances or the block above,
                    # but immediate feedback can be useful if desired.
                    # print("No instances found matching your new criteria.")
                    pass


            elif choice == str(option_number_dynamic): # Reset filter & Refresh OR Refresh
                if is_filtered:
                    print("Resetting filter and refreshing instances...")
                else:
                    # This case implies force_refresh=True because it's a manual refresh action
                    pass # Message is handled by get_instances_with_cache_logic
                all_instances = get_instances_with_cache_logic(force_refresh=True)
                current_display_instances = all_instances
                is_filtered = False
            
            elif choice == str(option_number_quit): # Quit
                break
            
            else:
                print("Invalid choice.")

    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
