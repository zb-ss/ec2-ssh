# EC2 Connect Utility

A command-line tool to easily list, search, and SSH into your AWS EC2 instances across all regions. It also provides SSH key management and SSH agent integration.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Python**: Version 3.8 or higher.
2.  **pipx**: For isolated installation of Python CLI applications. If you don't have it, you can install it by following the instructions [here](https://pipx.pypa.io/stable/installation/).
3.  **AWS CLI**: Configured with your AWS credentials and default region. The tool uses `boto3` which relies on the AWS CLI configuration (e.g., `~/.aws/credentials` and `~/.aws/config`). Ensure your credentials have the necessary permissions to describe EC2 instances and regions.
4.  **SSH Client**: An SSH client installed on your system (standard on most Linux and macOS systems, available on Windows via OpenSSH or PuTTY).
5.  **(Optional) SSH Agent**: For a smoother experience with SSH keys, it's recommended to have an SSH agent running.

## Installation

1.  Clone this repository or download the source code.
2.  Navigate to the root directory of the project (the directory containing `pyproject.toml`).
3.  Install the application using `pipx`:

    ```bash
    pipx install .
    ```

    This will install the `ec2-ssh` command-line tool in an isolated environment.

    If you later make changes to the source code and want to update your installed version, run the same command again from the project directory:
    ```bash
    pipx install . --force
    ```

## Usage

Once installed, you can run the application by typing:

```bash
ec2-ssh
```

This will launch the interactive command-line interface.

### Main Menu Options

Upon starting, the tool will fetch and display your EC2 instances. You will then see a menu with options like:

1.  **Connect to instance**: Select an instance from the list to SSH into. You'll be prompted for a username (defaults to `ec2-user`).
2.  **Manage SSH keys**:
    *   Set a default SSH key for all instances.
    *   Set a specific SSH key for a particular instance.
    *   View current key mappings.
    *   Add a key to a running SSH agent.
    *   List keys currently in the SSH agent.
3.  **Search/Filter instances**: Filter the displayed list of instances by name and/or type.
4.  **Refresh instances** / **Reset filter & Refresh instances**: Fetches the latest instance list from AWS. If a filter is active, this option will also reset the filter.
5.  **Quit**: Exit the application.

### SSH Key Management

*   The tool stores SSH key configurations in `~/.ec2_ssh_config.json`.
*   When connecting, if an SSH key is configured for an instance (or a default key is set), the tool will attempt to use it.
*   If an SSH agent is running and a key is specified, the tool will try to add the key to the agent for the current session.
*   If no key is configured for an instance, you will be prompted to enter the path to an SSH key file. You can then choose to save this key for the specific instance or as the default key.

### Searching Instances

You can filter the list of instances by:
*   **Name**: Enter a part of the instance name (case-insensitive).
*   **Type**: Enter a part of the instance type (e.g., `t2.micro`, `m5.large`, case-insensitive).

Leave a field blank if you don't want to filter by it.

### Instance List Caching

To improve performance, especially when you have many EC2 instances across multiple regions, the tool implements a caching mechanism for the instance list:

*   **How it works**: When instances are fetched from AWS, the list is saved to a local cache file (`~/.ec2_ssh_cache.json`) along with a timestamp.
*   **Cache Duration (TTL)**: By default, the cache is considered valid for 5 minutes. If you run the tool and the cache is still within this Time-To-Live (TTL), the instance list will be loaded from the cache, which is significantly faster.
*   **Automatic Refresh**: If the cache is older than the TTL, or if no cache file exists, the tool will automatically fetch fresh data from AWS and update the cache.
*   **Manual Refresh**: The "Refresh instances" option (or "Reset filter & Refresh instances") in the main menu will always bypass the cache, fetch the latest data directly from AWS, and then update the cache file.
*   **Data Freshness**: Be aware that if you are loading from the cache, any changes made to your EC2 instances in AWS (e.g., new instances, terminated instances, IP changes) since the cache was last updated will not be reflected until the cache expires or you perform a manual refresh.

## Development

If you want to run the script directly without installing it via `pipx` (e.g., for development):

1.  Ensure you have the dependencies installed. You can install them into your current Python environment or a virtual environment:
    ```bash
    pip install boto3 tabulate
    ```
    (Or, from the project root: `pip install .`)
2.  Run the main script:
    ```bash
    python src/ec2_ssh/main.py
    ```

## Troubleshooting

*   **AWS Credentials**: Ensure your AWS credentials are correctly configured and have permissions for `ec2:DescribeInstances` and `ec2:DescribeRegions`.
*   **SSH Agent Not Running**: If you see messages like "Could not open a connection to your authentication agent", you may need to start your SSH agent. On Linux/macOS, this is often done with `eval $(ssh-agent -s)`.
*   **Key Permissions**: SSH keys typically require strict permissions (e.g., `600` or `400`). The tool will warn you and offer to fix permissions if they are incorrect when adding a key.
```
