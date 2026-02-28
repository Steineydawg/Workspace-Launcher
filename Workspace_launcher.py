import subprocess
import tkinter as tk
import os
OPERA_PATH = r"C:\Users\noahs\AppData\Local\Programs\Opera GX\opera.exe"
DISCORD_EXE = r"C:\Users\noahs\AppData\Local\Discord\app-1.0.9226\Discord.exe"
DISCORD_ARGS = ["--processStart", "Discord.exe"]

def launch_workspace():
    # Launch Opera GX
    subprocess.Popen([OPERA_PATH])
    print("Discord exists?", os.path.exists(DISCORD_EXE))
    # Launch Discord
    subprocess.Popen([f'start "" "{DISCORD_EXE}" -- ProcessStart Discord.exe'], shell=True)
    
#Below is the UI
root = tk.Tk()
root.title("Workspace Launcher")
launch_button = tk.Button(root, text="open workspace", command=launch_workspace)
launch_button.pack()
root.mainloop()