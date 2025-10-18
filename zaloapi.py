import tkinter as tk
from tkinter import ttk, messagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import threading
from datetime import datetime
import json
import logging
import wmi
import re
import sys
import pyperclip
import openpyxl

current_version = "1.0.0.00010"

apiKey = 'AIzaSyDaKsphxv1-PkfagZ3M4PKCT3ybsVnx0Nk'
sheetId = '1fl3UFle_IwVY5-U_XYkpo1lS_fzpxVH47X3asF7TCmU'
rangeName = 'UIDKEYS!A2:A'
updateRangeName = 'UPDATE!B4:C4'

#python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
#python -m venv ZaloApi
#ZaloApi\Scripts\activate  # Trên Windows
#Set-ExecutionPolicy -Scope Process -ExecutionPolicy Unrestricted
#python zaloapi.py
#pip install pyinstaller
#pyinstaller --onefile --name=ZaloApi --noconsole zaloapi.py

# Setup logging
logging.basicConfig(filename='api_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ZaloAPITool:
    def __init__(self, root):
        self.root = root
        self.root.title("Zalo API Tool")
        self.root.geometry("1200x550")

        if not self.check_uid_and_activate():
            sys.exit(0)

        self.root.deiconify()

        self.is_running = {
            'addfriend': False, 'checkinfo': False, 'scangroup': False, 
            'sendmessages': False, 'getfriends': False, 'sendmessagefriends': False, 
            'sendmessagegroups': False, 'getgroups': False, 'sendmessagelistgroups': False,
            'invitegroups': False
        }
        self.cookies = []
        self.get_buttons = {}
        self.send_buttons = {}
        self.api_frames = {}
        self.selected_items = {
            'sendmessagefriends': set(),
            'sendmessagegroups': set(),
            'sendmessagelistgroups': set(),
            'invitegroups': set()
        }
        self.groups = []  # Store groups for dropdown
        self.setup_gui()

    def setup_gui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # Login Tab
        self.login_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.login_frame, text="Login")
        self.setup_login_tab()

        # API Tabs
        self.setup_api_tab('addfriend', 'Add Friend', 'UIDs', 'uid', 
                          result_columns=('STT', 'UID', 'Status', 'Time'), has_message=True)
        self.setup_api_tab('checkinfo', 'Check Info', 'Phones', 'phone', 
                          result_columns=('STT', 'Input', 'Zalo Name', 'Display Name', 'Status', 'UID', 'Time'))
        self.setup_api_tab('scangroup', 'Scan Group', 'Group ID', 'group_id', 
                          result_columns=('STT', 'Group ID', 'Group Name', 'Total Members', 'Member ID', 'Member Name', 'Time'))
        self.setup_api_tab('sendmessages', 'Send Messages', 'Phones or UIDs', 'phone', 
                          result_columns=('STT', 'Input', 'Status', 'Time'), has_message=True)
        self.setup_api_tab('getfriends', 'Get Friends', None, None, 
                          result_columns=('STT', 'userId', 'phoneNumber', 'displayName', 'zaloName', 'sdob', 'status'), 
                          has_message=False, has_list=False)
        self.setup_api_tab('sendmessagefriends', 'Send Messages to Friends', None, None, 
                          result_columns=('Select', 'STT', 'userId', 'phoneNumber', 'displayName', 'zaloName', 'sdob', 'status', 'Status'), 
                          has_message=True, has_list=False, has_selection=True)
        self.setup_api_tab('sendmessagegroups', 'Send Messages to Group Members', 'Group ID', 'group_id', 
                          result_columns=('Select', 'STT', 'Group ID', 'Group Name', 'Total Members', 'Member ID', 'Member Name', 'Time', 'Status'), 
                          has_message=True, has_list=True, has_selection=True)
        self.setup_api_tab('getgroups', 'Get Groups', None, None, 
                          result_columns=('STT', 'groupId', 'name', 'totalMember'), 
                          has_message=False, has_list=False)
        self.setup_api_tab('sendmessagelistgroups', 'Send Messages to List Groups', None, None, 
                          result_columns=('Select', 'STT', 'groupId', 'name', 'totalMember', 'Status'), 
                          has_message=True, has_list=False, has_selection=True)
        self.setup_invite_groups_tab()

    def setup_login_tab(self):
        ttk.Label(self.login_frame, text="Phone Number").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.phone_entry = ttk.Entry(self.login_frame)
        self.phone_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        ttk.Button(self.login_frame, text="Login", command=self.handle_login).grid(row=0, column=2, padx=5, pady=5)

        self.login_table = ttk.Treeview(self.login_frame, columns=('Phone', 'Cookie'), show='headings')
        self.login_table.heading('Phone', text='Phone Number')
        self.login_table.heading('Cookie', text='Cookie')
        self.login_table.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')
        self.login_frame.grid_columnconfigure(1, weight=1)
        self.login_frame.grid_rowconfigure(1, weight=1)

    def setup_invite_groups_tab(self):
        tab_type = 'invitegroups'
        tab_name = 'Invite Groups'
        result_columns = ('Select', 'STT', 'userId', 'phoneNumber', 'displayName', 'zaloName', 'sdob', 'status', 'Status')
        has_selection = True

        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=tab_name)
        self.api_frames[tab_type] = frame

        # Cookie selection
        ttk.Label(frame, text="Select Cookie").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].cookie_var = tk.StringVar()
        self.api_frames[tab_type].cookie_combo = ttk.Combobox(frame, textvariable=self.api_frames[tab_type].cookie_var, state='readonly')
        self.api_frames[tab_type].cookie_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.update_cookie_combobox(tab_type)

        # Group selection dropdown
        ttk.Label(frame, text="Select Group").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].group_var = tk.StringVar()
        self.api_frames[tab_type].group_combo = ttk.Combobox(frame, textvariable=self.api_frames[tab_type].group_var, state='readonly')
        self.api_frames[tab_type].group_combo.grid(row=0, column=3, padx=5, pady=5, sticky='ew')

        row_offset = 0

        # Timing inputs
        ttk.Label(frame, text="Thời Gian Nghỉ Mỗi Lần").grid(row=1+row_offset, column=0, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].item_delay_entry = ttk.Entry(frame)
        self.api_frames[tab_type].item_delay_entry.insert(0, "5")
        self.api_frames[tab_type].item_delay_entry.grid(row=1+row_offset, column=1, padx=5, pady=5, sticky='ew')

        ttk.Label(frame, text="Sẽ Nghỉ Khoảng Thời Gian").grid(row=1+row_offset, column=2, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].rest_time_entry = ttk.Entry(frame)
        self.api_frames[tab_type].rest_time_entry.insert(0, "10")
        self.api_frames[tab_type].rest_time_entry.grid(row=1+row_offset, column=3, padx=5, pady=5, sticky='ew')

        ttk.Label(frame, text="Sau Khi Thực Hiện").grid(row=2+row_offset, column=0, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].rest_after_entry = ttk.Entry(frame)
        self.api_frames[tab_type].rest_after_entry.insert(0, "100")
        self.api_frames[tab_type].rest_after_entry.grid(row=2+row_offset, column=1, padx=5, pady=5, sticky='ew')

        ttk.Label(frame, text="Dừng Sau Khi Hoàn Thành").grid(row=2+row_offset, column=2, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].stop_after_entry = ttk.Entry(frame)
        self.api_frames[tab_type].stop_after_entry.insert(0, "5000")
        self.api_frames[tab_type].stop_after_entry.grid(row=2+row_offset, column=3, padx=5, pady=5, sticky='ew')

        # Buttons
        self.get_buttons[tab_type] = ttk.Button(frame, text="Get", command=lambda: self.start_request(tab_type, None, False, False, is_get=True))
        self.get_buttons[tab_type].grid(row=3+row_offset, column=0, padx=5, pady=5)
        self.send_buttons[tab_type] = ttk.Button(frame, text="Invite", command=lambda: self.start_request(tab_type, None, False, False, is_get=False))
        self.send_buttons[tab_type].grid(row=3+row_offset, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Stop", command=lambda: self.stop_request(tab_type)).grid(row=3+row_offset, column=2, padx=5, pady=5)
        ttk.Button(frame, text="Export", command=lambda: self.export_table(tab_type)).grid(row=3+row_offset, column=3, padx=5, pady=5)

        # Result table with custom column widths
        self.api_frames[tab_type].result_table = ttk.Treeview(frame, columns=result_columns, show='headings')
        for col in result_columns:
            self.api_frames[tab_type].result_table.heading(col, text=col, command=lambda c=col: self.copy_column(tab_type, c))
            width = {
                'Select': 50,
                'STT': 50,
                'userId': 100,
                'phoneNumber': 100,
                'displayName': 100,
                'zaloName': 100,
                'sdob': 100,
                'status': 100,
                'Status': 200
            }.get(col, 150)
            self.api_frames[tab_type].result_table.column(col, width=width, anchor='center' if col == 'Select' else 'w')
        self.api_frames[tab_type].result_table.grid(row=4+row_offset, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')

        # Handle selection for checkbox
        def toggle_selection(event):
            item = self.api_frames[tab_type].result_table.identify_row(event.y)
            if item:
                current_values = self.api_frames[tab_type].result_table.item(item)['values']
                identifier = current_values[2]  # userId
                if item in self.selected_items[tab_type]:
                    self.selected_items[tab_type].remove(item)
                    current_values[0] = ''
                else:
                    self.selected_items[tab_type].add(item)
                    current_values[0] = '☑'
                self.api_frames[tab_type].result_table.item(item, values=current_values)

        self.api_frames[tab_type].result_table.bind('<Button-1>', toggle_selection)

        # Right-click context menu for "Select All"
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Select All", command=lambda: self.select_all(tab_type))
        def show_context_menu(event):
            context_menu.post(event.x_root, event.y_root)
        self.api_frames[tab_type].result_table.bind('<Button-3>', show_context_menu)

        # Add scrollbars
        y_scroll = ttk.Scrollbar(frame, orient='vertical', command=self.api_frames[tab_type].result_table.yview)
        y_scroll.grid(row=4+row_offset, column=5, sticky='ns')
        self.api_frames[tab_type].result_table.configure(yscrollcommand=y_scroll.set)
        x_scroll = ttk.Scrollbar(frame, orient='horizontal', command=self.api_frames[tab_type].result_table.xview)
        x_scroll.grid(row=5+row_offset, column=0, columnspan=5, sticky='ew')
        self.api_frames[tab_type].result_table.configure(xscrollcommand=x_scroll.set)

        self.api_frames[tab_type].result_table.bind('<Control-c>', lambda event: self.copy_selection())
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(4+row_offset, weight=1)

    def setup_api_tab(self, tab_type, tab_name, list_label, param_name, result_columns, has_message=False, has_list=True, has_selection=False):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=tab_name)
        self.api_frames[tab_type] = frame

        # Cookie selection
        ttk.Label(frame, text="Select Cookie").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].cookie_var = tk.StringVar()
        self.api_frames[tab_type].cookie_combo = ttk.Combobox(frame, textvariable=self.api_frames[tab_type].cookie_var, state='readonly')
        self.api_frames[tab_type].cookie_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.update_cookie_combobox(tab_type)

        row_offset = 0
        # Input type selection and list input
        if has_list and tab_type not in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups']:
            if tab_type in ['addfriend', 'sendmessages']:
                ttk.Label(frame, text="Input Type").grid(row=0, column=2, padx=5, pady=5, sticky='w')
                self.api_frames[tab_type].input_type_var = tk.StringVar(value="UID")
                input_type_combo = ttk.Combobox(frame, textvariable=self.api_frames[tab_type].input_type_var, 
                                                values=["Phone", "UID"], state='readonly')
                input_type_combo.grid(row=0, column=3, padx=5, pady=5, sticky='ew')

                self.api_frames[tab_type].list_label_var = tk.StringVar(value=f"List of {self.api_frames[tab_type].input_type_var.get()}s (one per line)")
                list_label_widget = ttk.Label(frame, textvariable=self.api_frames[tab_type].list_label_var)
                list_label_widget.grid(row=1, column=0, padx=5, pady=5, sticky='w')

                def update_list_label(*args):
                    self.api_frames[tab_type].list_label_var.set(f"List of {self.api_frames[tab_type].input_type_var.get()}s (one per line)")
                self.api_frames[tab_type].input_type_var.trace('w', update_list_label)
            else:
                ttk.Label(frame, text=f"List of {list_label} (one per line)").grid(row=1, column=0, padx=5, pady=5, sticky='w')

            self.api_frames[tab_type].list_text = tk.Text(frame, height=5)
            self.api_frames[tab_type].list_text.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky='ew')
            row_offset += 1

        # Message input
        if has_message:
            ttk.Label(frame, text="Message").grid(row=1+row_offset, column=0, padx=5, pady=5, sticky='w')
            self.api_frames[tab_type].message_text = tk.Text(frame, height=3)
            self.api_frames[tab_type].message_text.grid(row=1+row_offset, column=1, columnspan=3, padx=5, pady=5, sticky='ew')
            row_offset += 1

        # Timing inputs
        ttk.Label(frame, text="Thời Gian Nghỉ Mỗi Lần").grid(row=1+row_offset, column=0, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].item_delay_entry = ttk.Entry(frame)
        self.api_frames[tab_type].item_delay_entry.insert(0, "5")
        self.api_frames[tab_type].item_delay_entry.grid(row=1+row_offset, column=1, padx=5, pady=5, sticky='ew')

        ttk.Label(frame, text="Sẽ Nghỉ Khoảng Thời Gian").grid(row=1+row_offset, column=2, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].rest_time_entry = ttk.Entry(frame)
        self.api_frames[tab_type].rest_time_entry.insert(0, "10")
        self.api_frames[tab_type].rest_time_entry.grid(row=1+row_offset, column=3, padx=5, pady=5, sticky='ew')

        ttk.Label(frame, text="Sau Khi Thực Hiện").grid(row=2+row_offset, column=0, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].rest_after_entry = ttk.Entry(frame)
        self.api_frames[tab_type].rest_after_entry.insert(0, "100")
        self.api_frames[tab_type].rest_after_entry.grid(row=2+row_offset, column=1, padx=5, pady=5, sticky='ew')

        ttk.Label(frame, text="Dừng Sau Khi Hoàn Thành").grid(row=2+row_offset, column=2, padx=5, pady=5, sticky='w')
        self.api_frames[tab_type].stop_after_entry = ttk.Entry(frame)
        self.api_frames[tab_type].stop_after_entry.insert(0, "5000")
        self.api_frames[tab_type].stop_after_entry.grid(row=2+row_offset, column=3, padx=5, pady=5, sticky='ew')

        # Buttons
        button_text = "Get" if tab_type in ['sendmessagefriends', 'sendmessagegroups', 'sendmessagelistgroups', 'getfriends', 'getgroups'] else "Start"
        self.get_buttons[tab_type] = ttk.Button(frame, text=button_text, command=lambda: self.start_request(tab_type, param_name, has_message, has_list, is_get=button_text=="Get"))
        self.get_buttons[tab_type].grid(row=3+row_offset, column=0, padx=5, pady=5)
        
        if tab_type in ['sendmessagefriends', 'sendmessagegroups', 'sendmessagelistgroups']:
            self.send_buttons[tab_type] = ttk.Button(frame, text="Send", command=lambda: self.start_request(tab_type, param_name, has_message, has_list, is_get=False))
            self.send_buttons[tab_type].grid(row=3+row_offset, column=1, padx=5, pady=5)
            ttk.Button(frame, text="Stop", command=lambda: self.stop_request(tab_type)).grid(row=3+row_offset, column=2, padx=5, pady=5)
            ttk.Button(frame, text="Export", command=lambda: self.export_table(tab_type)).grid(row=3+row_offset, column=3, padx=5, pady=5)
        else:
            ttk.Button(frame, text="Stop", command=lambda: self.stop_request(tab_type)).grid(row=3+row_offset, column=1, padx=5, pady=5)
            ttk.Button(frame, text="Export", command=lambda: self.export_table(tab_type)).grid(row=3+row_offset, column=2, padx=5, pady=5)

        # Result table with custom column widths
        self.api_frames[tab_type].result_table = ttk.Treeview(frame, columns=result_columns, show='headings')
        for col in result_columns:
            self.api_frames[tab_type].result_table.heading(col, text=col, command=lambda c=col: self.copy_column(tab_type, c))
            # Default width for most columns
            width = 50 if col == 'Select' else 50 if col == 'STT' else 150
            # Custom widths for specific tabs
            if tab_type == 'sendmessagefriends':
                width = {
                    'Select': 50,
                    'STT': 50,
                    'userId': 100,
                    'phoneNumber': 100,
                    'displayName': 100,
                    'zaloName': 100,
                    'sdob': 100,
                    'status': 100,
                    'Status': 200
                }.get(col, 150)
            elif tab_type == 'sendmessagegroups':
                width = {
                    'Select': 50,
                    'STT': 50,
                    'Group ID': 100,
                    'Group Name': 100,
                    'Total Members': 100,
                    'Member ID': 100,
                    'Member Name': 100,
                    'Time': 100,
                    'Status': 200
                }.get(col, 150)
            elif tab_type == 'sendmessagelistgroups':
                width = {
                    'Select': 50,
                    'STT': 50,
                    'groupId': 100,
                    'name': 100,
                    'totalMember': 100,
                    'Status': 200
                }.get(col, 150)
            self.api_frames[tab_type].result_table.column(col, width=width, anchor='center' if col == 'Select' else 'w')
        self.api_frames[tab_type].result_table.grid(row=4+row_offset, column=0, columnspan=5, padx=5, pady=5, sticky='nsew')

        # Handle selection for checkbox
        if has_selection:
            def toggle_selection(event):
                item = self.api_frames[tab_type].result_table.identify_row(event.y)
                if item:
                    current_values = self.api_frames[tab_type].result_table.item(item)['values']
                    identifier = current_values[2] if tab_type in ['sendmessagefriends', 'sendmessagelistgroups'] else current_values[5]
                    if item in self.selected_items[tab_type]:
                        self.selected_items[tab_type].remove(item)
                        current_values[0] = ''
                    else:
                        self.selected_items[tab_type].add(item)
                        current_values[0] = '☑'
                    self.api_frames[tab_type].result_table.item(item, values=current_values)

            self.api_frames[tab_type].result_table.bind('<Button-1>', toggle_selection)

            # Right-click context menu for "Select All"
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Select All", command=lambda: self.select_all(tab_type))
            def show_context_menu(event):
                context_menu.post(event.x_root, event.y_root)
            self.api_frames[tab_type].result_table.bind('<Button-3>', show_context_menu)

        # Add scrollbars
        y_scroll = ttk.Scrollbar(frame, orient='vertical', command=self.api_frames[tab_type].result_table.yview)
        y_scroll.grid(row=4+row_offset, column=5, sticky='ns')
        self.api_frames[tab_type].result_table.configure(yscrollcommand=y_scroll.set)
        x_scroll = ttk.Scrollbar(frame, orient='horizontal', command=self.api_frames[tab_type].result_table.xview)
        x_scroll.grid(row=5+row_offset, column=0, columnspan=5, sticky='ew')
        self.api_frames[tab_type].result_table.configure(xscrollcommand=x_scroll.set)

        self.api_frames[tab_type].result_table.bind('<Control-c>', lambda event: self.copy_selection())
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(4+row_offset, weight=1)

    def check_uid_and_activate(self):
        url = f'https://sheets.googleapis.com/v4/spreadsheets/{sheetId}/values/{rangeName}?key={apiKey}'
        activation_key = self.generate_fixed_key()

        try:
            res = requests.get(url)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            messagebox.showerror("Lỗi kết nối", f"Không thể kiểm tra kích hoạt: {e}")
            return False

        keys = data.get('values', [])
        uid_with_date_name = next((item[0] for item in keys if activation_key in item[0] and item[0].endswith("|ok")), None)

        if uid_with_date_name is None:
            self.show_activation_dialog(activation_key)
            return False
        else:
            parts = uid_with_date_name.split("|")
            try:
                expiry_date = datetime.strptime(parts[1], "%d/%m/%Y")
                name = parts[2]
            except Exception:
                messagebox.showerror("Lỗi", "Dữ liệu ngày không hợp lệ.")
                return False

            days_left = (expiry_date - datetime.now()).days
            if days_left <= 0:
                self.show_expired_dialog(activation_key, name)
                return False

            self.root.title(f"ZALO API --- User {name} còn lại {days_left} ngày --- Version {current_version}")
            return True

    def show_activation_dialog(self, activation_key):
        messagebox.showinfo("Chưa kích hoạt", f"Gửi UID cho Admin để kích hoạt:\n{activation_key}")
        pyperclip.copy(activation_key)

    def show_expired_dialog(self, activation_key, name):
        messagebox.showinfo("Hết hạn", f"Chào {name}, phần mềm đã hết hạn.\nUID: {activation_key}")
        pyperclip.copy(activation_key)

    def generate_fixed_key(self):
        info = self.get_windows_device_info()
        info_2_first_char = info[2][0] if info[2] and info[2][0].isalpha() else ''
        info_2_numbers = ''.join(re.findall(r'[0-9]', info[2][1:]))
        formatted_info = f"ZALOAPI{info_2_first_char}{info_2_numbers} {info[3]} {info[4]} {info[5]} {info[6]}GB{info[7]}"
        filtered_info = ''.join(re.findall(r'[A-Z0-9]', formatted_info))
        return filtered_info

    def get_windows_device_info(self):
        try:
            c = wmi.WMI()
            os_info = c.Win32_OperatingSystem()[0]
            system_info = c.Win32_ComputerSystem()[0]
            bios_info = c.Win32_BIOS()[0]

            os_name = os_info.Caption
            os_version = os_info.Version
            manufacturer = system_info.Manufacturer
            model = system_info.Model
            serial = bios_info.SerialNumber
            release_date = bios_info.ReleaseDate[:8]
            ram = int(system_info.TotalPhysicalMemory) // (1024 ** 3)
            disk_count = len(c.Win32_LogicalDisk())

            return os_name, os_version, manufacturer, model, serial, release_date, ram, disk_count
        except Exception as e:
            print(f"Lỗi lấy thông tin máy: {e}")
            return '', '', '', '', '', '', 0, 0

    def select_all(self, tab_type):
        for item in self.api_frames[tab_type].result_table.get_children():
            current_values = self.api_frames[tab_type].result_table.item(item)['values']
            if item not in self.selected_items[tab_type]:
                self.selected_items[tab_type].add(item)
                current_values[0] = '☑'
                self.api_frames[tab_type].result_table.item(item, values=current_values)
        print(f"[INFO] Selected all items in {tab_type}")

    def copy_column(self, tab_type, column):
        table = self.api_frames[tab_type].result_table
        column_values = [table.item(item)['values'][table['columns'].index(column)] for item in table.get_children()]
        if column_values:
            self.root.clipboard_clear()
            self.root.clipboard_append('\n'.join(str(val) for val in column_values))
            print(f"[INFO] Copied column {column} to clipboard")
        else:
            messagebox.showwarning("Warning", f"No data in column {column} to copy.")

    def copy_selection(self):
        current_tab = self.notebook.select()
        if not current_tab:
            return
        tab_index = self.notebook.index(current_tab)
        table = self.notebook.winfo_children()[tab_index].result_table
        selected_items = table.selection()
        if not selected_items:
            return
        data = []
        for item in selected_items:
            values = table.item(item)['values']
            data.append('\t'.join(str(v) for v in values))
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(data))
        print(f"[INFO] Copied selected rows to clipboard")

    def update_cookie_combobox(self, tab_type):
        self.api_frames[tab_type].cookie_combo['values'] = [f"{c['cookie'][:20]}..." for c in self.cookies]

    def update_group_combobox(self, tab_type):
        self.api_frames[tab_type].group_combo['values'] = [f"{g['name']} (ID: {g['groupId']})" for g in self.groups]

    def handle_login(self):
        phone = self.phone_entry.get().strip()
        if not phone:
            messagebox.showerror("Error", "Please enter a phone number.")
            return
        threading.Thread(target=self.get_cookie, args=(phone,), daemon=True).start()

    def get_cookie(self, phone):
        options = Options()
        driver = webdriver.Chrome(options=options)
        try:
            print(f"[INFO] Starting login for phone: {phone}")
            driver.get('https://id.zalo.me/')
            WebDriverWait(driver, 300).until(EC.url_to_be('https://chat.zalo.me/'))
            cookies = driver.get_cookies()
            cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
            print(f"[SUCCESS] Captured cookie for phone {phone}: {cookie_string[:100]}...")
            logging.debug(f"Captured cookie for phone {phone}: {cookie_string}")
            
            for i, entry in enumerate(self.cookies):
                if entry['phone'] == phone:
                    self.cookies[i]['cookie'] = cookie_string
                    print(f"[INFO] Updated cookie for existing phone {phone}")
                    break
            else:
                self.cookies.append({'phone': phone, 'cookie': cookie_string})
                print(f"[INFO] Added new cookie for phone {phone}")
                
            self.root.after(0, self.update_login_table)
            for tab_type in self.api_frames:
                self.root.after(0, lambda t=tab_type: self.update_cookie_combobox(t))
        except Exception as e:
            error_msg = f"[ERROR] Failed to get cookie for phone {phone}: {str(e)}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            logging.error(f"Cookie capture failed for phone {phone}: {str(e)}")
        finally:
            driver.quit()

    def update_login_table(self):
        for item in self.login_table.get_children():
            self.login_table.delete(item)
        for cookie in self.cookies:
            self.login_table.insert('', 'end', values=(cookie['phone'], cookie['cookie'][:50] + '...'))

    def disable_all_buttons(self):
        for tab_type in self.get_buttons:
            self.get_buttons[tab_type].config(state='disabled')
        for tab_type in self.send_buttons:
            self.send_buttons[tab_type].config(state='disabled')

    def enable_all_buttons(self):
        for tab_type in self.get_buttons:
            self.get_buttons[tab_type].config(state='normal')
        for tab_type in self.send_buttons:
            self.send_buttons[tab_type].config(state='normal')

    def start_request(self, tab_type, param_name, has_message, has_list=True, is_get=False):
        if self.is_running[tab_type]:
            print(f"[WARNING] {tab_type} is already running")
            return
        self.is_running[tab_type] = True
        self.root.after(0, self.disable_all_buttons)

        cookie = self.api_frames[tab_type].cookie_var.get()
        if not cookie:
            print("[ERROR] No cookie selected")
            messagebox.showerror("Error", "Please select a cookie.")
            self.is_running[tab_type] = False
            self.root.after(0, self.enable_all_buttons)
            return
        selected = next((c for c in self.cookies if f"{c['cookie'][:20]}..." == cookie), None)
        if not selected:
            print("[ERROR] Selected cookie not found")
            messagebox.showerror("Error", "Selected cookie not found.")
            self.is_running[tab_type] = False
            self.root.after(0, self.enable_all_buttons)
            return
        cookie = selected['cookie']
        print(f"[INFO] Using cookie for {tab_type}: {cookie[:50]}...")

        items = []
        if has_list and tab_type not in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups']:
            items = self.api_frames[tab_type].list_text.get("1.0", tk.END).strip().split('\n')
            items = [item.strip() for item in items if item.strip()]
        message = self.api_frames[tab_type].message_text.get("1.0", tk.END).strip() if has_message else ''
        print(f"[INFO] {tab_type} inputs: {len(items)} items, message: {message[:20] + '...' if message else 'None'}")

        try:
            item_delay = float(self.api_frames[tab_type].item_delay_entry.get())
            rest_time = float(self.api_frames[tab_type].rest_time_entry.get()) * 60
            rest_after = int(self.api_frames[tab_type].rest_after_entry.get())
            stop_after = int(self.api_frames[tab_type].stop_after_entry.get())
            print(f"[INFO] Timing settings: item_delay={item_delay}s, rest_time={rest_time}s, rest_after={rest_after}, stop_after={stop_after}")
        except ValueError:
            print("[ERROR] Invalid timing values")
            messagebox.showerror("Error", "Invalid timing values.")
            self.is_running[tab_type] = False
            self.root.after(0, self.enable_all_buttons)
            return

        if has_list and tab_type not in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups'] and not items or (has_message and not message and not is_get):
            print("[ERROR] Missing required fields")
            messagebox.showerror("Error", "Please fill in all required fields.")
            self.is_running[tab_type] = False
            self.root.after(0, self.enable_all_buttons)
            return

        threading.Thread(target=self.process_requests, args=(tab_type, param_name, cookie, items, message, item_delay, rest_after, rest_time, stop_after, is_get), daemon=True).start()

    def stop_request(self, tab_type):
        self.is_running[tab_type] = False
        print(f"[INFO] Stopped {tab_type}")
        self.root.after(0, self.enable_all_buttons)

    def process_requests(self, tab_type, param_name, cookie, items, message, item_delay, rest_after, rest_time, stop_after, is_get):
        api_urls = {
            'addfriend': 'https://hongvippro.com/zalo/addfriend.php',
            'checkinfo': 'https://hongvippro.com/zalo/checkinfo.php',
            'scangroup': 'https://hongvippro.com/zalo/scangroup1.php',
            'sendmessages': 'https://hongvippro.com/zalo/sendmessages.php',
            'getfriends': 'https://hongvippro.com/zalo/getfriends.php',
            'sendmessagefriends': 'https://hongvippro.com/zalo/sendmessages.php',
            'sendmessagegroups': 'https://hongvippro.com/zalo/sendmessages.php',
            'getgroups': 'https://hongvippro.com/zalo/getnhom.php',
            'sendmessagelistgroups': 'https://hongvippro.com/zalo/sendmessages_nhom.php',
            'invitegroups': 'https://hongvippro.com/zalo/invitegroup.php'
        }
        stt = 0
        current_time = datetime.now().strftime('%H:%M:%S')
        current_date = datetime.now().strftime('%Y-%m-%d')
        formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
        if tab_type in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups']:
            items = ['']

        for i, item in enumerate(items):
            if not self.is_running[tab_type]:
                print(f"[INFO] Stopped {tab_type} processing")
                break

            if stt >= stop_after:
                print(f"[INFO] Stopped {tab_type} after reaching {stop_after} items")
                break

            original_item = item
            input_type = self.api_frames[tab_type].input_type_var.get() if tab_type in ['addfriend', 'sendmessages'] else None

            # Prepare API request data
            if tab_type == 'addfriend':
                if input_type == 'UID':
                    data = {'cookie': cookie, 'uid': item, 'message': formatted_message}
                elif input_type == 'Phone':
                    data = {'cookie': cookie, 'phone': item, 'message': formatted_message}
                print(f"[INFO] Sending addfriend request for: {item}")

            elif tab_type == 'sendmessages':
                if input_type == 'Phone':
                    current_time = datetime.now().strftime('%H:%M:%S')
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
                    data = {'cookie': cookie, 'phone': item, 'message': formatted_message}
                elif input_type == 'UID':
                    current_time = datetime.now().strftime('%H:%M:%S')
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
                    data = {'cookie': cookie, 'uid': item, 'message': formatted_message}
                print(f"[INFO] Sending sendmessages request for: {item}")

            elif tab_type == 'checkinfo':
                data = {'cookie': cookie, 'phone': item}
                print(f"[INFO] Sending checkinfo request for input: {item}")

            elif tab_type == 'scangroup':
                mpage = 1
                saved_group_name = 'N/A'
                while self.is_running[tab_type] and stt < stop_after:
                    data = {'cookie': cookie, 'group_id': str(item), 'mpage': str(mpage)}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        logging.debug(f"Sending request to {api_urls[tab_type]}: {data}")
                        response = requests.post(api_urls[tab_type], data=data, headers=headers)
                        print(f"[RESPONSE] {tab_type} (item: {original_item}, page: {mpage}): Status {response.status_code}")
                        logging.debug(f"Response: {response.text[:500]}")

                        result = json.loads(response.text)
                        if result.get('status') == 'Success' and result.get('data', {}).get('error_code') == 0:
                            group_data = result['data']['data']
                            group_id = group_data.get('groupId', 'N/A')
                            group_name = group_data.get('name') or saved_group_name
                            total_members = group_data.get('totalMember', 'N/A')
                            members = group_data.get('currentMems', [])

                            if mpage == 1 and group_name != 'N/A':
                                saved_group_name = group_name

                            for member in members:
                                if stt >= stop_after:
                                    break
                                stt += 1
                                values = (
                                    stt, group_id, group_name, total_members,
                                    member.get('id', 'N/A'), member.get('dName', 'N/A'),
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                )
                                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                                print(f"[RESULT] {tab_type}: Member={member.get('dName')}")

                            if group_data.get('hasMoreMember') == 0:
                                break
                            mpage += 1
                            time.sleep(item_delay)
                        else:
                            error_msg = result.get('data', {}).get('error_message', 'Unknown error')
                            logging.error(f"{tab_type} failed: {error_msg}")
                            break
                    except Exception as e:
                        logging.error(f"{tab_type} request failed: {str(e)}")
                        break
                continue

            elif tab_type == 'getfriends':
                data = {'cookie': cookie}
                print(f"[INFO] Fetching friends")

            elif tab_type == 'getgroups':
                data = {'cookie': cookie}
                print(f"[INFO] Fetching groups")

            elif tab_type == 'sendmessagefriends':
                if is_get:
                    data = {'cookie': cookie}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post(api_urls['getfriends'], data=data, headers=headers)
                        print(f"[RESPONSE] getfriends: Status {response.status_code}, Content={response.text[:100]}...")
                        logging.debug(f"Response for getfriends: Status={response.status_code}, Content={response.text[:500]}")

                        result = json.loads(response.text)
                        if result.get('error_code') == 0:
                            friends = result.get('data', [])
                            for friend in friends:
                                if stt >= stop_after:
                                    print(f"[INFO] Stopped {tab_type} after reaching {stop_after} items")
                                    break
                                stt += 1
                                values = (
                                    '', stt, friend.get('userId', 'N/A'), friend.get('phoneNumber', 'N/A'),
                                    friend.get('displayName', 'N/A'), friend.get('zaloName', 'N/A'),
                                    friend.get('sdob', 'N/A'), friend.get('status', 'N/A')[:50], 'N/A'
                                )
                                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                                print(f"[RESULT] {tab_type}: Friend={friend.get('displayName')}, userId={friend.get('userId')}")
                            self.selected_items[tab_type].clear()
                        else:
                            error_msg = f"Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}"
                            print(f"[RESULT] {tab_type}: {error_msg}")
                            logging.error(f"{tab_type} failed: {error_msg}")
                    except Exception as e:
                        result_text = f"Request failed: {str(e)}"
                        print(f"[ERROR] {tab_type}: {result_text}")
                        logging.error(f"Request failed for {tab_type}: {str(e)}")
                    continue
                else:
                    selected_friends = []
                    for item_id in self.selected_items[tab_type]:
                        values = self.api_frames[tab_type].result_table.item(item_id)['values']
                        selected_friends.append({'uid': values[2], 'name': values[4], 'item_id': item_id})
                    if not selected_friends:
                        print("[ERROR] No friends selected")
                        messagebox.showerror("Error", "Please select at least one friend to send messages to.")
                        self.is_running[tab_type] = False
                        self.root.after(0, self.enable_all_buttons)
                        return

                    for friend in selected_friends:
                        if not self.is_running[tab_type]:
                            print(f"[INFO] Stopped {tab_type} processing")
                            break
                        if stt >= stop_after:
                            print(f"[INFO] Stopped {tab_type} after reaching {stop_after} items")
                            break
                        stt += 1
                        uid = friend['uid']
                        name = friend['name']
                        item_id = friend['item_id']
                        current_time = datetime.now().strftime('%H:%M:%S')
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
                        friend_message = formatted_message.replace('{name}', name)
                        data = {'cookie': cookie, 'uid': uid, 'message': friend_message}
                        print(f"[INFO] Sending message to friend: {name} (UID: {uid})")

                        try:
                            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                            response = requests.post(api_urls[tab_type], data=data, headers=headers)
                            print(f"[RESPONSE] {tab_type} (friend: {name}): Status {response.status_code}, Content={response.text[:100]}...")
                            logging.debug(f"Response for {tab_type} (friend: {name}): Status={response.status_code}, Content={response.text[:500]}")

                            result = json.loads(response.text)
                            current_values = self.api_frames[tab_type].result_table.item(item_id)['values']
                            if result.get('status') == 'Successfully':
                                current_values[-1] = f"✅ Success (MsgID: {result.get('msgId', 'N/A')})"
                                print(f"[RESULT] {tab_type} (friend: {name}): Status=Successfully, MsgID={result.get('msgId', 'N/A')}")
                            else:
                                error_msg = result.get('message', '❌ Failed')
                                current_values[-1] = error_msg[:50]
                                print(f"[RESULT] {tab_type} (friend: {name}): {error_msg}")
                                logging.error(f"{tab_type} failed for {name}: {error_msg}")

                            self.root.after(0, lambda v=current_values, iid=item_id: self.api_frames[tab_type].result_table.item(iid, values=v))

                            if stt % rest_after == 0 and stt > 0 and stt < stop_after:
                                print(f"[INFO] Resting for {rest_time} seconds after {rest_after} items")
                                time.sleep(rest_time)

                            print(f"[DEBUG] Sleeping for {item_delay}s")
                            time.sleep(item_delay)

                        except json.JSONDecodeError as e:
                            result_text = f"Non-JSON response: {response.text[:100]}..."
                            current_values = self.api_frames[tab_type].result_table.item(item_id)['values']
                            current_values[-1] = result_text[:50]
                            print(f"[ERROR] {tab_type} (friend: {name}): {result_text}")
                            logging.error(f"Non-JSON response for {tab_type}: {response.text[:500]}")
                            self.root.after(0, lambda v=current_values, iid=item_id: self.api_frames[tab_type].result_table.item(iid, values=v))
                        except Exception as e:
                            result_text = f"Request failed: {str(e)}"
                            current_values = self.api_frames[tab_type].result_table.item(item_id)['values']
                            current_values[-1] = result_text[:50]
                            print(f"[ERROR] {tab_type} (friend: {name}): {result_text}")
                            logging.error(f"Request failed for {tab_type}: {str(e)}")
                            self.root.after(0, lambda v=current_values, iid=item_id: self.api_frames[tab_type].result_table.item(iid, values=v))
                    continue

            elif tab_type == 'sendmessagegroups':
                if is_get:
                    mpage = 1
                    saved_group_name = 'N/A'
                    while self.is_running[tab_type] and stt < stop_after:
                        data = {'cookie': cookie, 'group_id': str(item), 'mpage': str(mpage)}
                        try:
                            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                            logging.debug(f"Sending request to {api_urls['scangroup']}: {data}")
                            response = requests.post(api_urls['scangroup'], data=data, headers=headers)
                            print(f"[RESPONSE] {tab_type} (item: {original_item}, page: {mpage}): Status {response.status_code}")
                            logging.debug(f"Response: {response.text[:500]}")

                            result = json.loads(response.text)
                            if result.get('status') == 'Success' and result.get('data', {}).get('error_code') == 0:
                                group_data = result['data']['data']
                                group_id = group_data.get('groupId', 'N/A')
                                group_name = group_data.get('name') or saved_group_name
                                total_members = group_data.get('totalMember', 'N/A')
                                members = group_data.get('currentMems', [])

                                if mpage == 1 and group_name != 'N/A':
                                    saved_group_name = group_name

                                for member in members:
                                    if stt >= stop_after:
                                        break
                                    stt += 1
                                    values = (
                                        '', stt, group_id, group_name, total_members,
                                        member.get('id', 'N/A'), member.get('dName', 'N/A'),
                                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'N/A'
                                    )
                                    self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                                    print(f"[RESULT] {tab_type}: Member={member.get('dName')}")

                                if group_data.get('hasMoreMember') == 0:
                                    break
                                mpage += 1
                                time.sleep(item_delay)
                            else:
                                error_msg = result.get('data', {}).get('error_message', 'Unknown error')
                                logging.error(f"{tab_type} failed: {error_msg}")
                                break
                        except Exception as e:
                            logging.error(f"{tab_type} request failed: {str(e)}")
                            break
                    self.selected_items[tab_type].clear()
                    continue
                else:
                    selected_members = []
                    for item_id in self.selected_items[tab_type]:
                        values = self.api_frames[tab_type].result_table.item(item_id)['values']
                        selected_members.append({'member_id': values[5], 'name': values[6], 'item_id': item_id})
                    if not selected_members:
                        messagebox.showerror("Error", "No group members selected.")
                        self.is_running[tab_type] = False
                        self.root.after(0, self.enable_all_buttons)
                        return

                    for member in selected_members:
                        if not self.is_running[tab_type] or stt >= stop_after:
                            break
                        stt += 1
                        current_time = datetime.now().strftime('%H:%M:%S')
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
                        data = {'cookie': cookie, 'uid': member['member_id'], 'message': formatted_message.replace('{name}', member['name'])}
                        try:
                            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                            response = requests.post(api_urls[tab_type], data=data, headers=headers)
                            result = json.loads(response.text)
                            current_values = self.api_frames[tab_type].result_table.item(member['item_id'])['values']
                            current_values[-1] = f"✅ Success (MsgID: {result.get('msgId', 'N/A')})" if result.get('status') == 'Successfully' else f"❌ {result.get('message', 'Failed')}"
                            self.root.after(0, lambda v=current_values, iid=member['item_id']: self.api_frames[tab_type].result_table.item(iid, values=v))
                            print(f"[RESULT] {tab_type}: {member['name']} - {'Success' if result.get('status') == 'Successfully' else 'Failed'}")
                            time.sleep(item_delay)
                        except Exception as e:
                            current_values = self.api_frames[tab_type].result_table.item(member['item_id'])['values']
                            current_values[-1] = f"❌ {str(e)}"
                            self.root.after(0, lambda v=current_values, iid=member['item_id']: self.api_frames[tab_type].result_table.item(iid, values=v))
                            logging.error(f"{tab_type} failed: {str(e)}")
                            print(f"[ERROR] {tab_type}: {member['name']} - Failed: {str(e)}")
                        if stt % rest_after == 0 and stt < stop_after:
                            time.sleep(rest_time)
                    continue

            elif tab_type == 'sendmessagelistgroups':
                if is_get:
                    data = {'cookie': cookie}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post(api_urls['getgroups'], data=data, headers=headers)
                        print(f"[RESPONSE] getgroups: Status {response.status_code}, Content={response.text[:100]}...")
                        logging.debug(f"Response for getgroups: Status={response.status_code}, Content={response.text[:500]}")

                        result = json.loads(response.text)
                        if result.get('error_code') == 0:
                            groups = result.get('data', [])
                            for group in groups:
                                if stt >= stop_after:
                                    break
                                stt += 1
                                values = (
                                    '', stt, group.get('groupId', 'N/A'), group.get('name', 'N/A'),
                                    group.get('totalMember', 'N/A'), 'N/A'
                                )
                                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                                print(f"[RESULT] {tab_type}: Group={group.get('name')}")
                            self.selected_items[tab_type].clear()
                        else:
                            error_msg = f"Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}"
                            print(f"[RESULT] {tab_type}: {error_msg}")
                            logging.error(f"{tab_type} failed: {error_msg}")
                    except Exception as e:
                        result_text = f"Request failed: {str(e)}"
                        print(f"[ERROR] {tab_type}: {result_text}")
                        logging.error(f"Request failed for {tab_type}: {str(e)}")
                    continue
                else:
                    selected_groups = []
                    for item_id in self.selected_items[tab_type]:
                        values = self.api_frames[tab_type].result_table.item(item_id)['values']
                        selected_groups.append({'group_id': values[2], 'name': values[3], 'item_id': item_id})
                    if not selected_groups:
                        messagebox.showerror("Error", "No groups selected.")
                        self.is_running[tab_type] = False
                        self.root.after(0, self.enable_all_buttons)
                        return

                    for group in selected_groups:
                        if not self.is_running[tab_type] or stt >= stop_after:
                            break
                        stt += 1
                        current_time = datetime.now().strftime('%H:%M:%S')
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
                        data = {'cookie': cookie, 'group_id': group['group_id'], 'message': formatted_message.replace('{name}', group['name'])}
                        try:
                            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                            response = requests.post(api_urls[tab_type], data=data, headers=headers)
                            result = json.loads(response.text)
                            current_values = self.api_frames[tab_type].result_table.item(group['item_id'])['values']
                            current_values[-1] = f"✅ Success (MsgID: {result.get('data', {}).get('data', {}).get('msgId', 'N/A')})" if result.get('status') == 'Success' else f"❌ {result.get('data', {}).get('error_message', 'Failed')}"
                            self.root.after(0, lambda v=current_values, iid=group['item_id']: self.api_frames[tab_type].result_table.item(iid, values=v))
                            print(f"[RESULT] {tab_type}: {group['name']} - {'Success' if result.get('status') == 'Success' else 'Failed'}")
                            time.sleep(item_delay)
                        except Exception as e:
                            current_values = self.api_frames[tab_type].result_table.item(group['item_id'])['values']
                            current_values[-1] = f"❌ {str(e)}"
                            self.root.after(0, lambda v=current_values, iid=group['item_id']: self.api_frames[tab_type].result_table.item(iid, values=v))
                            logging.error(f"{tab_type} failed: {str(e)}")
                            print(f"[ERROR] {tab_type}: {group['name']} - Failed: {str(e)}")
                        if stt % rest_after == 0 and stt < stop_after:
                            time.sleep(rest_time)
                    continue

            elif tab_type == 'invitegroups':
                if is_get:
                    # Fetch friends and groups (GIỮ NGUYÊN)
                    friends_data = {'cookie': cookie}
                    groups_data = {'cookie': cookie}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        # Fetch friends
                        friends_response = requests.post(api_urls['getfriends'], data=friends_data, headers=headers)
                        print(f"[RESPONSE] getfriends: Status {friends_response.status_code}")
                        friends_result = json.loads(friends_response.text)

                        # Fetch groups and update dropdown
                        groups_response = requests.post(api_urls['getgroups'], data=groups_data, headers=headers)
                        print(f"[RESPONSE] getgroups: Status {groups_response.status_code}")
                        groups_result = json.loads(groups_response.text)

                        if friends_result.get('error_code') == 0 and groups_result.get('error_code') == 0:
                            self.groups = groups_result.get('data', [])
                            self.root.after(0, lambda: self.update_group_combobox(tab_type))
                            friends = friends_result.get('data', [])
                            for friend in friends:
                                if stt >= stop_after:
                                    break
                                stt += 1
                                values = (
                                    '', stt, friend.get('userId', 'N/A'), friend.get('phoneNumber', 'N/A'),
                                    friend.get('displayName', 'N/A'), friend.get('zaloName', 'N/A'),
                                    friend.get('sdob', 'N/A'), friend.get('status', 'N/A')[:50], 'N/A'
                                )
                                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                            self.selected_items[tab_type].clear()
                        else:
                            error_msg = f"Friends Error {friends_result.get('error_code')}: {friends_result.get('error_message')} | Groups Error {groups_result.get('error_code')}: {groups_result.get('error_message')}"
                            print(f"[RESULT] {tab_type}: {error_msg}")
                    except Exception as e:
                        print(f"[ERROR] {tab_type}: {str(e)}")
                    continue
                
                else:
                    # 🚀 INVITE BATCH - MỚI HOÀN TOÀN
                    selected_group = self.api_frames[tab_type].group_var.get()
                    if not selected_group:
                        messagebox.showerror("Error", "Please select a group.")
                        self.is_running[tab_type] = False
                        self.root.after(0, self.enable_all_buttons)
                        return
                    
                    group_id = next((g['groupId'] for g in self.groups if f"{g['name']} (ID: {g['groupId']})" == selected_group), None)
                    group_name = next((g['name'] for g in self.groups if f"{g['name']} (ID: {g['groupId']})" == selected_group), 'N/A')
                    if not group_id:
                        messagebox.showerror("Error", "Selected group not found.")
                        self.is_running[tab_type] = False
                        self.root.after(0, self.enable_all_buttons)
                        return

                    selected_friends = []
                    for item_id in self.selected_items[tab_type]:
                        values = self.api_frames[tab_type].result_table.item(item_id)['values']
                        selected_friends.append({'uid': values[2], 'name': values[4], 'item_id': item_id})
                    
                    if not selected_friends:
                        messagebox.showerror("Error", "Please select at least one friend to invite.")
                        self.is_running[tab_type] = False
                        self.root.after(0, self.enable_all_buttons)
                        return

                    # 🎯 BATCH INVITE - FIX UID STRING
                    uids_list = ','.join([str(friend['uid']) for friend in selected_friends])  # 🔥 FIX ĐÂY!
                    current_time = datetime.now().strftime('%H:%M:%S')
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else 'Xin mời bạn tham gia nhóm nhé!'
                    
                    data = {
                        'cookie': cookie,
                        'group_id': str(group_id),  # 🔥 CŨNG FIX STRING
                        'uid': uids_list,
                        'message': formatted_message
                    }
                    
                    batch_size = len(selected_friends)
                    print(f"[INFO] 🚀 Batch inviting {batch_size} friends to group {group_name} (ID: {group_id})")
                    print(f"[INFO] UIDs: {uids_list[:100]}...")
                    print(f"[INFO] Message: {formatted_message[:50]}...")

                    try:
                        # 🔥 GỬI POST ĐẾN PHP API MỚI
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post('https://hongvippro.com/zalo/invitegroup.php', data=data, headers=headers)
                        print(f"[RESPONSE] Batch invite: Status {response.status_code}")
                        logging.debug(f"Batch invite response: {response.text}")

                        result = json.loads(response.text)
                        
                        if result.get('status') == 'Success':
                            # ✅ THÀNH CÔNG - Update tất cả rows
                            success_msg = f"✅ Batch Success ({batch_size} friends)"
                            for friend in selected_friends:
                                current_values = self.api_frames[tab_type].result_table.item(friend['item_id'])['values']
                                current_values[-1] = success_msg[:50]
                                self.root.after(0, lambda v=current_values, iid=friend['item_id']: 
                                              self.api_frames[tab_type].result_table.item(iid, values=v))
                            print(f"[SUCCESS] 🎉 Invited {batch_size} friends to {group_name}")
                            stt += batch_size
                            
                        else:
                            # ❌ LỖI - Update từng row
                            error_msg = result.get('error', 'Failed')
                            for friend in selected_friends:
                                current_values = self.api_frames[tab_type].result_table.item(friend['item_id'])['values']
                                current_values[-1] = f"❌ {error_msg[:40]}"
                                self.root.after(0, lambda v=current_values, iid=friend['item_id']: 
                                              self.api_frames[tab_type].result_table.item(iid, values=v))
                            print(f"[ERROR] Batch failed: {error_msg}")

                    except Exception as e:
                        error_msg = f"Request failed: {str(e)}"
                        for friend in selected_friends:
                            current_values = self.api_frames[tab_type].result_table.item(friend['item_id'])['values']
                            current_values[-1] = f"❌ {error_msg[:40]}"
                            self.root.after(0, lambda v=current_values, iid=friend['item_id']: 
                                          self.api_frames[tab_type].result_table.item(iid, values=v))
                        print(f"[ERROR] Batch invite exception: {error_msg}")

                    # ⏱️ DELAY SAU BATCH
                    time.sleep(item_delay)
                    if stt % rest_after == 0 and stt < stop_after:
                        print(f"[INFO] Resting {rest_time}s after {rest_after} items")
                        time.sleep(rest_time)
                    continue

            else:
                data = {'cookie': cookie, param_name: item}
                print(f"[INFO] Sending {tab_type} request for {param_name}: {item}")

            try:
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                print(f"[REQUEST] Sending to {api_urls[tab_type]} with data: {data}")
                logging.debug(f"Sending request to {api_urls[tab_type]} with data: {data}, headers: {headers}")
                response = requests.post(api_urls[tab_type], data=data, headers=headers)
                print(f"[RESPONSE] {tab_type} (item: {original_item}): Status {response.status_code}, Content={response.text[:100]}...")
                logging.debug(f"Response for {tab_type} (item: {original_item}): Status {response.status_code}, Content: {response.text[:500]}")

                result = json.loads(response.text)
                if tab_type == 'addfriend':
                    stt += 1
                    if 'error' in result:
                        values = (stt, original_item, f"❌ {result.get('error', 'Unknown error')}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    else:
                        values = (
                            stt, original_item,
                            f"✅ Success (Status: {result.get('data', {}).get('status', 'N/A')}, Is Friend: {result.get('data', {}).get('is_friend', 'N/A')})" if result.get('error_code') == 0 else f"❌ Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}",
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                elif tab_type == 'sendmessages':
                    stt += 1
                    values = (
                        stt, original_item,
                        f"✅ Success (MsgID: {result.get('msgId', 'N/A')})" if result.get('status') == 'Successfully' else f"❌ {result.get('message', 'Failed')}",
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    )
                elif tab_type == 'checkinfo':
                    stt += 1
                    if result.get('error_code') == 0:
                        data = result.get('data', {})
                        values = (
                            stt, original_item, data.get('zalo_name', 'N/A'), data.get('display_name', 'N/A'),
                            data.get('status', 'N/A')[:50], data.get('uid', 'N/A'),
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                    else:
                        values = (
                            stt, original_item, 'N/A', 'N/A', f"❌ Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}", 'N/A',
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        )
                elif tab_type == 'getfriends':
                    if result.get('error_code') == 0:
                        friends = result.get('data', [])
                        for friend in friends:
                            if stt >= stop_after:
                                break
                            stt += 1
                            values = (
                                stt, friend.get('userId', 'N/A'), friend.get('phoneNumber', 'N/A'),
                                friend.get('displayName', 'N/A'), friend.get('zaloName', 'N/A'),
                                friend.get('sdob', 'N/A'), friend.get('status', 'N/A')[:50]
                            )
                            self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                        continue
                    else:
                        logging.error(f"{tab_type} failed: {result.get('error_message', 'Unknown error')}")
                        continue
                elif tab_type == 'getgroups':
                    if result.get('error_code') == 0:
                        groups = result.get('data', [])
                        for group in groups:
                            if stt >= stop_after:
                                break
                            stt += 1
                            values = (
                                stt, group.get('groupId', 'N/A'), group.get('name', 'N/A'),
                                group.get('totalMember', 'N/A')
                            )
                            self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
                        continue
                    else:
                        logging.error(f"{tab_type} failed: {result.get('error_message', 'Unknown error')}")
                        continue
                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
            except json.JSONDecodeError as e:
                result_text = f"Non-JSON response: {response.text[:100]}..."
                if tab_type == 'addfriend':
                    stt += 1
                    values = (stt, original_item, result_text[:50], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                elif tab_type == 'sendmessages':
                    stt += 1
                    values = (stt, original_item, result_text[:50], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                elif tab_type == 'checkinfo':
                    stt += 1
                    values = (stt, original_item, 'N/A', 'N/A', result_text[:50], 'N/A', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    logging.error(f"Non-JSON response for {tab_type}: {response.text[:500]}")
                    continue
                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))
            except Exception as e:
                result_text = f"Request failed: {str(e)}"
                if tab_type == 'addfriend':
                    stt += 1
                    values = (stt, original_item, result_text[:50], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                elif tab_type == 'sendmessages':
                    stt += 1
                    values = (stt, original_item, result_text[:50], datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                elif tab_type == 'checkinfo':
                    stt += 1
                    values = (stt, original_item, 'N/A', 'N/A', result_text[:50], 'N/A', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    logging.error(f"Request failed for {tab_type}: {str(e)}")
                    continue
                self.root.after(0, lambda v=values: self.api_frames[tab_type].result_table.insert('', 'end', values=v))

            if tab_type not in ['scangroup', 'getfriends', 'sendmessagefriends', 'sendmessagegroups', 'getgroups', 'sendmessagelistgroups', 'invitegroups'] and stt % rest_after == 0 and stt < stop_after:
                time.sleep(rest_time)
            if tab_type not in ['scangroup', 'getfriends', 'sendmessagefriends', 'sendmessagegroups', 'getgroups', 'sendmessagelistgroups', 'invitegroups']:
                time.sleep(item_delay)

        self.is_running[tab_type] = False
        self.root.after(0, self.enable_all_buttons)

    def export_table(self, tab_type):
        table = self.api_frames[tab_type].result_table
        data = [table.item(item)['values'] for item in table.get_children()]
        if not data:
            messagebox.showwarning("Warning", "No data to export.")
            return
        
        # 🔥 SỬ DỤNG OPENPYXL ĐỂ XUẤT XLSX
        columns = [table.heading(col)['text'] for col in table['columns']]
        filename = f"{tab_type}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        # Tạo workbook và worksheet
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Results"
        
        # Ghi header
        ws.append(columns)
        
        # Ghi data - Giữ nguyên số lớn bằng cách chuyển thành string
        for row in data:
            formatted_row = []
            for cell in row:
                try:
                    # Nếu là số và lớn hơn 15 chữ số, chuyển thành string
                    if isinstance(cell, (int, float)) and len(str(abs(int(cell)))) > 15:
                        formatted_row.append(str(cell))
                    else:
                        formatted_row.append(str(cell))
                except (ValueError, TypeError):
                    formatted_row.append(str(cell))
            ws.append(formatted_row)
        
        # Lưu file
        wb.save(filename)
        messagebox.showinfo("Success", f"✅ Exported {len(data)} rows to {filename}")
        print(f"[SUCCESS] Exported {filename}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ZaloAPITool(root)
    root.mainloop()