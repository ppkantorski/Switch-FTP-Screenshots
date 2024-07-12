import sys
import ftplib
import os
import time
import configparser
from datetime import datetime
from PyQt5 import QtWidgets, QtGui, QtCore
import threading
import webbrowser
from plyer import notification

# Import win10toast for Windows notifications
if sys.platform == 'win32':
    from winotify import Notification, audio
elif sys.platform == 'darwin':  # macOS specific imports
    from Foundation import NSObject, NSUserNotification, NSUserNotificationCenter, NSUserNotificationDefaultSoundName

    class NotificationDelegate(NSObject):
        def userNotificationCenter_didActivateNotification_(self, center, notification):
            userInfo = notification.userInfo()
            log_message(f"Notification clicked. User info: {userInfo}")
            if userInfo:
                file_path = userInfo.get('file_path')
                log_message(f"Attempting to open file path: {file_path}")
                if file_path:
                    os.system(f'open "{file_path}"')


TITLE = "Switch FTP Screenshots"
VERSION = "0.1.5"
AUTHOR = "ppkantorski"

# Determine the directory where the script is located
if getattr(sys, 'frozen', False):
    script_dir = sys._MEIPASS
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the config.ini file
config_path = os.path.join(script_dir, 'config.ini')

# Ensure the config.ini file exists, create a default one if not
if not os.path.exists(config_path):
    default_config = """[FTP]
SERVER = X.X.X.X
PORT = 5000
USER = root
PASS = 

[LOCAL]
OUTPUT_PATH = /path/to/save/files/

[SETTINGS]
CHECK_RATE = 20
DT_FORMAT = %Y-%m-%d_%H-%M-%S
AUTO_START = False
"""
    with open(config_path, 'w') as config_file:
        config_file.write(default_config)

# Read configuration from config.ini
config = configparser.ConfigParser(interpolation=None)  # Disable interpolation
config.read(config_path)

# FTP server details
SERVER = config.get('FTP', 'server')
PORT = config.getint('FTP', 'port')
USER = config.get('FTP', 'user')
PASS = config.get('FTP', 'pass')
PATH = "/emuMMC/RAW1/Nintendo/Album/"

# Local directory to save files
OUTPUT_PATH = config.get('LOCAL', 'output_path')
CHECK_RATE = int(config.get('SETTINGS', 'check_rate'))
DT_FORMAT = config.get('SETTINGS', 'dt_format')
AUTO_START = config.getboolean('SETTINGS', 'auto_start')

running = False
stop_event = threading.Event()

def log_message(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


# Explicitly keep a reference to the delegate to prevent garbage collection
notification_delegate = None

def notify_new_file(file_name, local_file_path=""):
    global notification_delegate
    message = f"New file {file_name} has been added."
    if sys.platform == 'darwin':  # macOS
        notification = NSUserNotification.alloc().init()
        notification.setTitle_(TITLE)
        notification.setInformativeText_(message)
        notification.setSoundName_(NSUserNotificationDefaultSoundName)
        notification.setUserInfo_({'file_path': local_file_path})
        
        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        notification_delegate = NotificationDelegate.alloc().init()
        center.setDelegate_(notification_delegate)
        log_message("Delegate set for notification center")
        center.deliverNotification_(notification)
        log_message(f"Notification sent for new file: {file_name} with path: {local_file_path}")
    elif sys.platform == 'win32':  # Windows
        try:
            icon_path = os.path.join(script_dir, "icon.ico")
            toast = Notification(app_id=TITLE,
                                 title=TITLE,
                                 msg=message,
                                 icon=icon_path)
            toast.set_audio(audio.Default, loop=False)
            toast.add_actions(label="Open File", launch=local_file_path)
            toast.show()
            log_message(f"Notification sent for new file: {file_name}")
        except Exception as e:
            log_message(f"Failed to send notification: {e}")
    else:
        try:
            notification.notify(
                title="FTP Screenshots",
                message=message,
                app_name=TITLE,
                app_icon=os.path.join(script_dir, "icon.png"),  # path to your app icon
                timeout=10  # Notification will disappear after 10 seconds
            )
            log_message(f"Notification sent for new file: {file_name}")
        except Exception as e:
            log_message(f"Failed to send notification: {e}")

def connect_ftp():
    ftp = ftplib.FTP()
    ftp.connect(SERVER, PORT, timeout=10)  # Set timeout for connection
    ftp.login(USER, PASS)
    return ftp

def list_files(ftp, path):
    file_list = []
    try:
        ftp.cwd(path)
        files = ftp.nlst()
        for file in files:
            full_path = os.path.join(path, file)
            try:
                ftp.cwd(full_path)
                file_list.extend(list_files(ftp, full_path))
                ftp.cwd('..')
            except ftplib.error_perm:
                file_list.append(full_path)
    except ftplib.error_perm:
        pass
    return file_list

def download_file(ftp, remote_file, local_file):
    with open(local_file, 'wb') as f:
        ftp.retrbinary(f'RETR {remote_file}', f.write)

def format_filename(file_name, dt_format):
    base_name, extension = os.path.splitext(file_name)
    try:
        timestamp_str = base_name.split('-')[0]
        timestamp_dt = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S%f')
        formatted_str = timestamp_dt.strftime(dt_format)
        return formatted_str
    except ValueError:
        return base_name

def clear_screen():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

def delete_line():
    print("\033[F\033[K", end='')

def screenshots():
    global running
    connection_success = False
    initial_loop = True
    was_last_message = False
    while running and not stop_event.is_set():
        start_time = time.time()
        try:
            ftp = connect_ftp()
            current_files = list_files(ftp, PATH)
            if connection_success and was_last_message:
                delete_line()
            log_message(f"FTP Connection to {SERVER} successful.")
            connection_success = True
            was_last_message = True
            for file in current_files:
                file_name = os.path.basename(file)
                formatted_name = file_name
                if DT_FORMAT:
                    formatted_name = format_filename(file_name, DT_FORMAT) + os.path.splitext(file_name)[1]
                    local_file_path = os.path.join(OUTPUT_PATH, formatted_name)
                else:
                    local_file_path = os.path.join(OUTPUT_PATH, file_name)
                if not os.path.exists(local_file_path):
                    try:
                        download_file(ftp, file, local_file_path)
                        log_message(f"Downloaded: {file}")
                        notify_new_file(formatted_name, local_file_path)
                        was_last_message = False
                    except Exception as e:
                        log_message(f"Error downloading {file}: {e}")
                        was_last_message = False
            ftp.quit()
        except ftplib.all_errors as e:
            if not connection_success and not initial_loop:
                delete_line()
            log_message(f"Error connecting to FTP server: {e}")
            connection_success = False
        except Exception as e:
            log_message(f"Unexpected error: {e}")
            connection_success = False
        
        initial_loop = False
        elapsed_time = time.time() - start_time
        sleep_time = max(0, CHECK_RATE - elapsed_time)
        time.sleep(sleep_time)
        
    log_message(f"FTP screenshots service has been stopped.")

def reload_config():
    global SERVER, PORT, USER, PASS, PATH, OUTPUT_PATH, CHECK_RATE, DT_FORMAT, AUTO_START
    config.read(config_path)
    SERVER = config.get('FTP', 'SERVER')
    PORT = config.getint('FTP', 'PORT')
    USER = config.get('FTP', 'USER')
    PASS = config.get('FTP', 'PASS')
    #PATH = config.get('FTP', 'PATH')
    OUTPUT_PATH = config.get('LOCAL', 'OUTPUT_PATH')
    CHECK_RATE = int(config.get('SETTINGS', 'CHECK_RATE'))
    DT_FORMAT = config.get('SETTINGS', 'DT_FORMAT')
    AUTO_START = config.get('SETTINGS', 'AUTO_START')

class ConfigDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure FTP Screenshots")
        self.layout = QtWidgets.QFormLayout(self)
        self.setFixedWidth(450)

        self.config_items = {}
        for section in config.sections():
            if section != 'DEFAULT':
                if section != 'FTP':
                    self.layout.addRow(QtWidgets.QLabel(""))
                label = QtWidgets.QLabel(f"{section}")
                font = label.font()
                font.setBold(True)
                label.setFont(font)
                self.layout.addRow(label)
                self.layout.addRow(QtWidgets.QFrame())
            for key, value in config.items(section):
                item_label = key
                line_edit = QtWidgets.QLineEdit(value)
                line_edit.setAlignment(QtCore.Qt.AlignRight)  # Align text to the right
                self.config_items[f"{section}.{key}"] = line_edit
                if key == 'auto_start':
                    continue
                elif section == 'LOCAL' and key == 'output_path':
                    browse_button = QtWidgets.QPushButton('\uD83D\uDCC2')  # Folder icon
                    browse_button.clicked.connect(self.select_output_directory)
                    hbox = QtWidgets.QHBoxLayout()
                    line_edit.setFixedWidth(240)  # Adjust the width of the input box
                    hbox.addWidget(line_edit)
                    hbox.addWidget(browse_button)
                    self.layout.addRow(QtWidgets.QLabel(f"  {item_label} "), hbox)
                else:
                    line_edit.setFixedWidth(300)  # Adjust the width of the input box
                    self.layout.addRow(QtWidgets.QLabel(f"  {item_label} "), line_edit)  # Added indent for key name

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.update_config)
        self.button_box.rejected.connect(self.reject)
        self.layout.addRow(self.button_box)

    def select_output_directory(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir_path:
            if not dir_path.endswith('/'):
                dir_path += '/'
            self.config_items['LOCAL.output_path'].setText(dir_path)

    def update_config(self):
        try:
            for item_label, line_edit in self.config_items.items():
                section, key = item_label.split('.')
                config.set(section, key, line_edit.text())
            with open(config_path, 'w') as configfile:
                config.write(configfile)
            QtWidgets.QMessageBox.information(self, "Success", "Configuration updated successfully.")
            reload_config()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to update configuration: {e}")
        self.accept()  # Close the dialog

class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Switch FTP Screenshots")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.setFixedSize(400, 250)

        icon_path = os.path.join(script_dir, "icon.png")
        if os.path.exists(icon_path):
            icon_label = QtWidgets.QLabel()
            pixmap = QtGui.QPixmap(icon_path).scaled(80, 80, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(QtCore.Qt.AlignCenter)
            self.layout.addWidget(icon_label)

        title_label = QtWidgets.QLabel(f"{TITLE} v{VERSION}")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        font = title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        self.layout.addWidget(title_label)

        author_label = QtWidgets.QLabel(f"Created by {AUTHOR}")
        author_label.setAlignment(QtCore.Qt.AlignCenter)
        self.layout.addWidget(author_label)

        github_button = QtWidgets.QPushButton("View on GitHub")
        github_button.clicked.connect(lambda: webbrowser.open("https://github.com/ppkantorski/Switch-FTP-Screenshots"))
        self.layout.addWidget(github_button)

        ok_button = QtWidgets.QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        self.layout.addWidget(ok_button)

        self.layout.setAlignment(github_button, QtCore.Qt.AlignCenter)
        self.layout.setAlignment(ok_button, QtCore.Qt.AlignCenter)


class SystemTrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super(SystemTrayApp, self).__init__(icon, parent)
        self.setToolTip(f"{TITLE} v{VERSION}")
        self.parent = parent
        self.menu = QtWidgets.QMenu(parent)

        self.start_action = self.menu.addAction("\u25B6 Start Data Sync")
        self.auto_start_action = self.menu.addAction("    Auto-Start")
        self.menu.addSeparator()
        self.config_action = self.menu.addAction("Configure...")
        self.menu.addSeparator()
        self.about_action = self.menu.addAction("About Switch FTP Screenshots")
        self.menu.addSeparator()
        self.restart_action = self.menu.addAction("Restart")  # Add Restart action
        self.exit_action = self.menu.addAction("Quit")

        self.start_action.triggered.connect(self.toggle_capture)
        self.auto_start_action.triggered.connect(self.toggle_auto_start)
        self.config_action.triggered.connect(self.configure_config)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.restart_action.triggered.connect(self.restart_app)  # Connect Restart action to method
        self.exit_action.triggered.connect(self.exit_app)

        self.setContextMenu(self.menu)
        self.update_auto_start_action()

        if AUTO_START:
            self.start_capture()

    def toggle_capture(self):
        global running
        if running:
            self.stop_capture()
        else:
            self.start_capture()

    def start_capture(self):
        global running
        if not running:
            running = True
            stop_event.clear()
            threading.Thread(target=screenshots, daemon=True).start()
            self.start_action.setText("\u25A0 Stop Data Sync")
        else:
            log_message("FTP Screenshots Capture is already running")

    def stop_capture(self):
        global running
        if running:
            running = False
            stop_event.set()
            self.start_action.setText("\u25B6 Start Data Sync")
        else:
            log_message("FTP Screenshots Capture is not running")

    def toggle_auto_start(self):
        current_auto_start = config.getboolean('SETTINGS', 'AUTO_START')
        new_auto_start = not current_auto_start
        config.set('SETTINGS', 'AUTO_START', str(new_auto_start))
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        self.update_auto_start_action()
        reload_config()

    def update_auto_start_action(self):
        auto_start = config.getboolean('SETTINGS', 'AUTO_START')
        if auto_start:
            self.auto_start_action.setText("\u2713 Auto-Start")
        else:
            self.auto_start_action.setText("    Auto-Start")

    def configure_config(self):
        dialog = ConfigDialog()
        dialog.exec_()
        dialog.show()

    def show_about_dialog(self):
        dialog = AboutDialog()
        dialog.exec_()
        dialog.show()

    def restart_app(self):
        QtWidgets.QApplication.quit()
        QtCore.QProcess.startDetached(sys.executable, sys.argv)

    def exit_app(self):
        global running
        if running:
            running = False
            stop_event.set()
        QtWidgets.qApp.quit()

def main():
    app = QtWidgets.QApplication(sys.argv)

    def is_dark_mode():
        if sys.platform == 'darwin':
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
            )
            return "Dark" in result.stdout
        elif sys.platform == 'win32':
            import winreg
            try:
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0  # 0 means dark mode, 1 means light mode
            except Exception as e:
                log_message(f"Failed to read registry: {e}")
                return False
        return False

    # Select the appropriate icon based on the system appearance
    icon_name = "dark_taskbar.png" if is_dark_mode() else "light_taskbar.png"
    icon_path = os.path.join(script_dir, icon_name)
    if os.path.exists(icon_path):
        tray_icon = SystemTrayApp(QtGui.QIcon(icon_path))
    else:
        tray_icon = SystemTrayApp(app.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
    
    tray_icon.show()

    sys.exit(app.exec_())
if __name__ == "__main__":
    main()
