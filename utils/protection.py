import os
import sys
import time
import ctypes
import threading
import subprocess
import tkinter.messagebox as msgbox

BLACKLISTED_PROCESSES = {
    "x64dbg.exe", "x32dbg.exe", "ida64.exe", "ida.exe", 
    "processhacker.exe", "cheatengine-x86_64.exe", 
    "cheatengine-i386.exe", "ollydbg.exe", "wireshark.exe",
    "fiddler.exe", "httpdebuggerui.exe", "scylla.exe", 
    "scylla_x64.exe", "scylla_x86.exe", "decompiler.exe"
}

def is_debugger_present():
    if sys.platform != "win32":
        return False
    try:
        # Check standard debugger
        if ctypes.windll.kernel32.IsDebuggerPresent():
            return True
        # Check remote debugger
        is_attached = ctypes.c_bool(False)
        current_process = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.CheckRemoteDebuggerPresent(current_process, ctypes.byref(is_attached))
        if is_attached.value:
            return True
    except Exception:
        pass
    return False

def check_blacklisted_processes():
    try:
        # Get list of running processes on Windows
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
        output = subprocess.check_output(
            ["tasklist"],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        ).decode('utf-8', errors='ignore').lower()
        
        for proc in BLACKLISTED_PROCESSES:
            if proc in output:
                return True, proc
    except Exception:
        pass
    return False, None

def security_loop():
    while True:
        if is_debugger_present():
            terminate_application("Debugger detected. Access denied.")
            
        triggered, proc_name = check_blacklisted_processes()
        if triggered:
            terminate_application(f"Security violation: Blacklisted tool detected ({proc_name}). Access denied.")
            
        time.sleep(2)

def terminate_application(reason):
    try:
        msgbox.showerror("Security Warning", f"{reason}\n\nThis application will now terminate.")
    except Exception:
        pass
    os._exit(0)

def init_security_protection():
    # Perform initial checks synchronously
    if is_debugger_present():
        terminate_application("Debugger detected. Access denied.")
        
    triggered, proc_name = check_blacklisted_processes()
    if triggered:
        terminate_application(f"Security violation: Blacklisted tool detected ({proc_name}). Access denied.")
        
    # Start background loop
    t = threading.Thread(target=security_loop, daemon=True)
    t.start()
