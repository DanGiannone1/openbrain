"""
Pre-flight safety hook for Claude Code.

Intercepts Bash commands before execution and blocks dangerous patterns.
Exit codes:
  0 - Allow command to proceed
  2 - Block command (stderr fed back to Claude)
"""

import json
import re
import sys


DANGEROUS_PATTERNS = [
    (r'git\s+push\s+[^;&|]*--force(?!-with-lease)',
     "Use --force-with-lease instead of --force to prevent overwriting others' work"),
    (r'git\s+push\s+[^;&|]*(?<![a-z])-f\b(?!orce-with-lease)',
     "Use --force-with-lease instead of -f to prevent overwriting others' work"),
    (r'git\s+push\s+--mirror',
     "git push --mirror can overwrite entire remote repository"),
    (r'git\s+push\s+--all\s+.*--force',
     "Force pushing all branches can destroy remote history"),
    (r'git\s+reset\s+--hard',
     "git reset --hard destroys uncommitted work - use git stash first"),
    (r'git\s+clean\s+.*-[fdxX]',
     "git clean -fd permanently removes untracked files"),
    (r'git\s+push\s+origin\s+:main\b',
     "This deletes the main branch on remote"),
    (r'git\s+push\s+origin\s+:master\b',
     "This deletes the master branch on remote"),
    (r'git\s+push\s+.*--delete\s+(origin\s+)?(main|master)\b',
     "This deletes the main/master branch on remote"),
    (r'git\s+branch\s+-D\s+(main|master)\b',
     "Force deleting main/master branch - this is usually a mistake"),
    (r'git\s+filter-branch',
     "git filter-branch rewrites history and can corrupt the repository"),
    (r'git\s+reflog\s+expire\s+--all',
     "This destroys reflog entries needed for recovery"),
    (r'git\s+gc\s+--prune=now',
     "Immediate pruning removes objects that might be needed for recovery"),
    (r'curl\s+[^|]*\|\s*(bash|sh|zsh|ksh|python|ruby|perl)',
     "Piping curl to interpreter executes arbitrary code"),
    (r'wget\s+[^|]*\|\s*(bash|sh|zsh|ksh|python|ruby|perl)',
     "Piping wget to interpreter executes arbitrary code"),
    (r'curl\s+.*-o\s*-\s*.*\|\s*(bash|sh|zsh|ksh)',
     "Piping curl output to shell executes arbitrary code"),
    (r'source\s+<\(curl',
     "Sourcing from curl executes arbitrary code"),
    (r'source\s+<\(wget',
     "Sourcing from wget executes arbitrary code"),
    (r'\beval\s+["\']?\$',
     "eval with variable expansion is a code injection risk"),
    (r'base64\s+(-d|--decode)\s*.*\|\s*(bash|sh|python)',
     "Decoding and executing base64 content is dangerous"),
    (r'rm\s+(-[rf]+\s+)*["\']?/',
     "Recursive deletion from root is extremely dangerous"),
    (r'rm\s+(-[rf]+\s+)*["\']?~',
     "Recursive deletion of home directory"),
    (r'rm\s+-rf\s+\*',
     "rm -rf * can delete everything in current directory"),
    (r'\bshred\s+',
     "shred securely deletes files - unrecoverable"),
    (r'find\s+.*-delete',
     "find with -delete can recursively remove many files"),
    (r'find\s+.*-exec\s+rm',
     "find with rm can recursively remove many files"),
    (r'>\s*["\']?/(?!dev/null)[^/\s]+',
     "Redirecting to root-level files can corrupt system"),
    (r'truncate\s+-s\s*0',
     "truncate zeroes out files"),
    (r'dd\s+.*of=/dev/(sd[a-z]|nvme|hd[a-z]|vd[a-z])',
     "dd to block device would destroy disk data"),
    (r'dd\s+.*if=/dev/(zero|urandom)\s+.*of=/',
     "dd from zero/urandom to filesystem path destroys data"),
    (r'mkfs\.',
     "mkfs would format and destroy partition data"),
    (r'\bformat\s+[a-zA-Z]:',
     "Windows format command destroys drive data"),
    (r'diskpart',
     "diskpart can modify/destroy partition tables"),
    (r'chmod\s+(-R\s+)?777\s+["\']?/',
     "chmod 777 on system paths creates security vulnerabilities"),
    (r'chmod\s+(-R\s+)?777\s+["\']?~',
     "chmod 777 on home directory creates security vulnerabilities"),
    (r'chmod\s+-R\s+777\s+\.',
     "chmod -R 777 on current directory is a security risk"),
    (r'cat\s+["\']?~/.ssh/id_(rsa|ed25519|ecdsa)(?!\.pub)',
     "This would expose private SSH keys"),
    (r'cat\s+["\']?~/.aws/credentials',
     "This would expose AWS credentials"),
    (r'cat\s+["\']?~/.azure/',
     "This would expose Azure credentials"),
    (r'gcloud\s+auth\s+print-access-token',
     "This prints a live GCP access token - use with caution"),
    (r'gh\s+auth\s+token',
     "This prints your GitHub token - avoid exposing"),
    (r'printenv\s*\|\s*(curl|wget|nc)',
     "Exfiltrating environment variables"),
    (r'cat\s+.*\.(pem|key|p12)\b',
     "This would expose private keys/certificates"),
    (r'gcloud\s+projects\s+delete',
     "This deletes an entire GCP project"),
    (r'gcloud\s+pubsub\s+topics\s+delete',
     "This deletes Pub/Sub topics"),
    (r'gcloud\s+pubsub\s+subscriptions\s+delete',
     "This deletes Pub/Sub subscriptions"),
    (r'gcloud\s+run\s+services\s+delete',
     "This deletes Cloud Run services"),
    (r'gcloud\s+functions\s+delete',
     "This deletes Cloud Functions"),
    (r'gcloud\s+scheduler\s+jobs\s+delete',
     "This deletes Cloud Scheduler jobs"),
    (r'gcloud\s+secrets\s+delete',
     "This deletes secrets from Secret Manager"),
    (r'gcloud\s+compute\s+instances\s+delete',
     "This deletes compute instances"),
    (r'gsutil\s+(-m\s+)?rm\s+-r',
     "Recursive GCS deletion can cause data loss"),
    (r'bq\s+rm\s+(-f\s+)?-r',
     "Recursive BigQuery deletion"),
    (r'terraform\s+destroy',
     "terraform destroy removes infrastructure - requires confirmation"),
    (r'pulumi\s+destroy',
     "pulumi destroy removes infrastructure"),
    (r'az\s+group\s+delete',
     "This deletes an Azure resource group and all resources"),
    (r'az\s+cosmosdb\s+(database|collection)\s+delete',
     "This deletes Cosmos DB databases or collections"),
    (r'aws\s+s3\s+rm\s+.*--recursive',
     "Recursive S3 deletion can cause data loss"),
    (r'aws\s+ec2\s+terminate-instances',
     "This terminates EC2 instances"),
    (r'\bDROP\s+(DATABASE|TABLE|SCHEMA)\b',
     "DROP commands destroy database objects"),
    (r'\bTRUNCATE\s+TABLE\b',
     "TRUNCATE removes all data from table"),
    (r'\bDELETE\s+FROM\s+\S+\s*;',
     "DELETE without WHERE clause removes all rows"),
    (r'mongo.*--eval.*dropDatabase',
     "This drops an entire MongoDB database"),
    (r'docker\s+run\s+.*--privileged',
     "Docker --privileged mode allows container escape"),
    (r'docker\s+run\s+.*-v\s+/:/\w',
     "Mounting root filesystem in container is dangerous"),
    (r'docker\s+run\s+.*--pid\s*=?\s*host',
     "Host PID namespace access is a security risk"),
    (r'kill\s+-9\s+-1\b',
     "kill -9 -1 kills all user processes"),
    (r'kill\s+-9\s+1\b',
     "kill -9 1 attempts to kill init process"),
    (r'pkill\s+-9\s+(python|node|java)\b',
     "This kills all processes of that type"),
    (r'\b(shutdown|reboot|halt|poweroff|init\s+[06])\b',
     "System shutdown or reboot commands"),
    (r'taskkill\s+/F\s+/IM\s+\*',
     "Windows force kill with wildcard"),
    (r'Stop-Process\s+.*-Force',
     "PowerShell force kill"),
    (r'iptables\s+(-F|--flush)',
     "Flushing firewall rules removes all protection"),
    (r'ufw\s+disable',
     "This disables the firewall"),
    (r'gcloud\s+compute\s+firewall-rules\s+delete',
     "This deletes GCP firewall rules"),
    (r'nc\s+.*-e\s+/bin/(ba)?sh',
     "Netcat reverse shell"),
    (r':\(\)\s*\{\s*:\|:&\s*\}\s*;:',
     "Fork bomb would crash the system"),
    (r'fork\s*while\s*fork',
     "Fork bomb pattern"),
    (r'gh\s+repo\s+delete',
     "This deletes a GitHub repository"),
    (r'gh\s+release\s+delete',
     "This deletes a GitHub release"),
    (r'gh\s+pr\s+merge\s+.*--admin',
     "Admin merge bypasses branch protections"),
    (r'Invoke-Expression',
     "Invoke-Expression (IEX) executes arbitrary code - PowerShell eval"),
    (r'\bIEX\b',
     "IEX (Invoke-Expression) executes arbitrary code"),
    (r'Invoke-WebRequest.*\|.*Invoke-Expression',
     "Download and execute pattern - PowerShell equivalent of curl | bash"),
    (r'Invoke-WebRequest.*\|.*IEX',
     "Download and execute pattern - PowerShell equivalent of curl | bash"),
    (r'\bIWR\b.*\|.*IEX',
     "Download and execute pattern (IWR | IEX)"),
    (r'DownloadString.*\|.*Invoke-Expression',
     "Download and execute pattern via WebClient"),
    (r'DownloadString.*\|.*IEX',
     "Download and execute pattern via WebClient"),
    (r'Net\.WebClient.*DownloadString',
     "WebClient download - often used for malicious downloads"),
    (r'Remove-Item\s+.*-Recurse.*-Force',
     "Recursive forced deletion in PowerShell"),
    (r'Remove-Item\s+.*-Force.*-Recurse',
     "Recursive forced deletion in PowerShell"),
    (r'Remove-Item\s+["\']?[A-Z]:\\',
     "Deleting from drive root in PowerShell"),
    (r'Remove-Item\s+["\']?\\\\',
     "Deleting from UNC path in PowerShell"),
    (r'Set-ExecutionPolicy\s+(Unrestricted|Bypass)',
     "Disabling PowerShell execution policy reduces security"),
    (r'Set-MpPreference\s+.*-DisableRealtimeMonitoring\s+\$true',
     "Disabling Windows Defender real-time monitoring"),
    (r'Disable-WindowsOptionalFeature.*Windows-Defender',
     "Disabling Windows Defender"),
    (r'Remove-ItemProperty\s+.*HKLM:',
     "Removing registry keys from HKEY_LOCAL_MACHINE"),
    (r'Remove-Item\s+.*HKLM:',
     "Removing registry keys from HKEY_LOCAL_MACHINE"),
    (r'Set-ItemProperty\s+.*HKLM:.*\\Run',
     "Modifying startup registry keys - persistence technique"),
    (r'New-ItemProperty\s+.*HKLM:.*\\Run',
     "Adding startup registry keys - persistence technique"),
    (r'Stop-Service\s+.*-Force',
     "Force stopping Windows services"),
    (r'Remove-Service\s+',
     "Removing Windows services"),
    (r'Set-Service\s+.*-StartupType\s+Disabled',
     "Disabling Windows services"),
    (r'Get-Credential.*\|.*ConvertFrom-SecureString',
     "Extracting credentials in exportable format"),
    (r'ConvertFrom-SecureString',
     "Converting secure strings - potential credential exposure"),
    (r'Clear-EventLog',
     "Clearing Windows event logs - covering tracks"),
    (r'Remove-EventLog',
     "Removing Windows event logs"),
    (r'wevtutil\s+cl',
     "Clearing Windows event logs via wevtutil"),
    (r'Set-NetFirewallProfile\s+.*-Enabled\s+False',
     "Disabling Windows Firewall"),
    (r'netsh\s+advfirewall\s+set\s+.*state\s+off',
     "Disabling Windows Firewall via netsh"),
    (r'Disable-NetFirewallRule',
     "Disabling firewall rules"),
    (r'Invoke-WebRequest\s+.*-Method\s+Post.*\$env:',
     "Potential exfiltration of environment variables"),
    (r'Send-MailMessage.*\.(pem|key|env|credentials)',
     "Potential credential exfiltration via email"),
]

SHELL_WRAPPERS = [
    r'bash\s+-c\s+["\'](.+)["\']',
    r'sh\s+-c\s+["\'](.+)["\']',
    r'zsh\s+-c\s+["\'](.+)["\']',
    r'/bin/bash\s+-c\s+["\'](.+)["\']',
    r'/bin/sh\s+-c\s+["\'](.+)["\']',
    r'powershell\s+-[Cc]ommand\s+["\'](.+)["\']',
    r'powershell\.exe\s+-[Cc]ommand\s+["\'](.+)["\']',
    r'pwsh\s+-[Cc]ommand\s+["\'](.+)["\']',
    r'pwsh\s+-c\s+["\'](.+)["\']',
    r'powershell\s+-[Ee]ncodedCommand\s+(\S+)',
]


def check_command(command: str, depth: int = 0) -> tuple[bool, str]:
    if depth > 3:
        return False, ""

    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, reason

    for wrapper_pattern in SHELL_WRAPPERS:
        match = re.search(wrapper_pattern, command)
        if match:
            nested_cmd = match.group(1)
            is_dangerous, reason = check_command(nested_cmd, depth + 1)
            if is_dangerous:
                return True, f"Nested command blocked: {reason}"

    return False, ""


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    is_dangerous, reason = check_command(command)

    if is_dangerous:
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"BLOCKED by safety hook: {reason}"
            }
        }
        print(json.dumps(response))
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
