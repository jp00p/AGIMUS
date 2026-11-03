import asyncio
import os


async def run_make_backup():
    """
    util function that runs our `make db-backup` command
    returns the new hash from git
    """
    backup_info = {"url": "", "backup_name":""}
    os.system("make db-backup --no-print-directory")
    raw_new_backup = []
    with os.popen("make db-get-latest-backup --no-print-directory") as line:
        raw_new_backup = line.readlines()
        backup_info["backup_name"] = raw_new_backup[-1].replace("\n", "")
        raw_presigned_url = []
    with os.popen("make db-get-latest-backup-download-url --no-print-directory") as line:
        raw_presigned_url = line.readlines()
        backup_info["url"] = raw_presigned_url[-1].replace("\n", "")
    return backup_info


async def run_make_backup_from_command():
    """
    util function for our `!backup_database` discord command
    runs this using asyncio to prevent heartbeat blocking
    """
    await _run_make_capture_last_line(["make", "db-backup", "--no-print-directory"])
    
    backup_name = await _run_make_capture_last_line(
        ["make", "db-get-latest-backup", "--no-print-directory"]
    )
    
    url = await _run_make_capture_last_line(
        ["make", "db-get-latest-backup-download-url", "--no-print-directory"]
    )
    
    return {
        "backup_name": backup_name,
        "url": url
    }


async def _run_make_capture_last_line(cmd: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{stderr.decode('utf-8', errors='replace')}")
    lines = stdout.decode("utf-8", errors="replace").splitlines()
    return (lines[-1] if lines else "").strip()
