🚀 Workspace Launcher

A Windows desktop application built with Python and Tkinter that allows users to create custom app launch groups and launch them with a double-click.

🔥 Features

Scan installed apps (Start Menu + Desktop shortcuts)

Create custom launch groups

Save groups locally on the user's machine

Double-click a group to launch all apps

Edit and delete groups

Search/filter apps while creating groups

Optional "Run on Startup" toggle

Persistent local storage (JSON config)

🖥️ How It Works

The app scans common Windows shortcut locations:

Start Menu (ProgramData + AppData)

User Desktop

Public Desktop

It maps shortcut display names to file paths and stores selected app groups in:

C:\Users\<username>\AppData\Local\WorkspaceLauncher\app_groups.json

On launch, double-clicking a group opens all associated shortcuts with a slight delay for stability.

⚙️ Requirements

Windows OS

Python 3.10+

Tkinter (comes with standard Python installation)

▶️ Running the App

From project directory:

python Workspace_launcher.py
🚀 Startup Support

Enable Run on startup from inside the app.

This creates a .bat file in:

%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

Disabling removes it.

🧠 About This Project

The README was AI-generated for documentation clarity.

The code itself was written manually, with AI used only as an assistant for debugging and structural guidance — not copy-pasted blindly.

This project was built as part of a long-term software engineering learning journey.