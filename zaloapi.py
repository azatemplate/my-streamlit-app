import streamlit as st
import requests
import time
from datetime import datetime
import json
import logging
import pandas as pd

current_version = "1.0.0.00010"

# Setup logging
logging.basicConfig(filename='api_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# API URLs
API_URLS = {
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

def main():
    st.set_page_config(page_title="Zalo API Tool", layout="wide")
    st.title(f"Zalo API Tool - Version {current_version}")

    # Initialize session state
    if 'cookies' not in st.session_state:
        st.session_state.cookies = []
    if 'groups' not in st.session_state:
        st.session_state.groups = []
    if 'is_running' not in st.session_state:
        st.session_state.is_running = {key: False for key in API_URLS.keys()}
    if 'results' not in st.session_state:
        st.session_state.results = {key: [] for key in API_URLS.keys()}
    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = {
            'sendmessagefriends': set(),
            'sendmessagegroups': set(),
            'sendmessagelistgroups': set(),
            'invitegroups': set()
        }

    # Sidebar for cookie management
    with st.sidebar:
        st.header("Cookie Management")
        cookie_input = st.text_area("Enter Cookie String", height=100, placeholder="Paste your Zalo cookie here...")
        cookie_phone = st.text_input("Phone Number (for reference)", placeholder="Enter phone number")
        if st.button("Add Cookie"):
            if cookie_input and cookie_phone:
                st.session_state.cookies.append({'phone': cookie_phone, 'cookie': cookie_input.strip()})
                st.success(f"Added cookie for {cookie_phone}")
                logging.debug(f"Added cookie for phone {cookie_phone}: {cookie_input[:100]}...")
            else:
                st.error("Please provide both cookie and phone number.")

        # Display cookies
        if st.session_state.cookies:
            st.subheader("Stored Cookies")
            for cookie in st.session_state.cookies:
                st.write(f"Phone: {cookie['phone']}, Cookie: {cookie['cookie'][:20]}...")

    # Tabs for different functionalities
    tabs = st.tabs([
        "Add Friend", "Check Info", "Scan Group", "Send Messages", "Get Friends",
        "Send Messages to Friends", "Send Messages to Group Members", "Get Groups",
        "Send Messages to List Groups", "Invite Groups"
    ])

    # Tab configurations
    tab_configs = {
        'addfriend': {
            'name': 'Add Friend',
            'has_list': True,
            'has_message': True,
            'param_name': 'uid',
            'columns': ['STT', 'UID', 'Status', 'Time']
        },
        'checkinfo': {
            'name': 'Check Info',
            'has_list': True,
            'has_message': False,
            'param_name': 'phone',
            'columns': ['STT', 'Input', 'Zalo Name', 'Display Name', 'Status', 'UID', 'Time']
        },
        'scangroup': {
            'name': 'Scan Group',
            'has_list': True,
            'has_message': False,
            'param_name': 'group_id',
            'columns': ['STT', 'Group ID', 'Group Name', 'Total Members', 'Member ID', 'Member Name', 'Time']
        },
        'sendmessages': {
            'name': 'Send Messages',
            'has_list': True,
            'has_message': True,
            'param_name': 'phone',
            'columns': ['STT', 'Input', 'Status', 'Time']
        },
        'getfriends': {
            'name': 'Get Friends',
            'has_list': False,
            'has_message': False,
            'param_name': None,
            'columns': ['STT', 'userId', 'phoneNumber', 'displayName', 'zaloName', 'sdob', 'status']
        },
        'sendmessagefriends': {
            'name': 'Send Messages to Friends',
            'has_list': False,
            'has_message': True,
            'param_name': None,
            'columns': ['Select', 'STT', 'userId', 'phoneNumber', 'displayName', 'zaloName', 'sdob', 'status', 'Status'],
            'has_selection': True
        },
        'sendmessagegroups': {
            'name': 'Send Messages to Group Members',
            'has_list': True,
            'has_message': True,
            'param_name': 'group_id',
            'columns': ['Select', 'STT', 'Group ID', 'Group Name', 'Total Members', 'Member ID', 'Member Name', 'Time', 'Status'],
            'has_selection': True
        },
        'getgroups': {
            'name': 'Get Groups',
            'has_list': False,
            'has_message': False,
            'param_name': None,
            'columns': ['STT', 'groupId', 'name', 'totalMember']
        },
        'sendmessagelistgroups': {
            'name': 'Send Messages to List Groups',
            'has_list': False,
            'has_message': True,
            'param_name': None,
            'columns': ['Select', 'STT', 'groupId', 'name', 'totalMember', 'Status'],
            'has_selection': True
        },
        'invitegroups': {
            'name': 'Invite Groups',
            'has_list': False,
            'has_message': True,
            'param_name': None,
            'columns': ['Select', 'STT', 'userId', 'phoneNumber', 'displayName', 'zaloName', 'sdob', 'status', 'Status'],
            'has_selection': True
        }
    }

    for tab, tab_key in zip(tabs, tab_configs.keys()):
        with tab:
            config = tab_configs[tab_key]
            st.header(config['name'])

            # Cookie selection
            cookie_options = [f"{c['phone']}: {c['cookie'][:20]}..." for c in st.session_state.cookies]
            selected_cookie = st.selectbox("Select Cookie", cookie_options, key=f"cookie_{tab_key}")
            selected_cookie_data = next((c for c in st.session_state.cookies if f"{c['phone']}: {c['cookie'][:20]}..." == selected_cookie), None)

            # Group selection for invitegroups
            if tab_key == 'invitegroups':
                group_options = [f"{g['name']} (ID: {g['groupId']})" for g in st.session_state.groups]
                selected_group = st.selectbox("Select Group", group_options, key=f"group_{tab_key}")

            # Input fields
            if config['has_list'] and tab_key not in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups']:
                if tab_key in ['addfriend', 'sendmessages']:
                    input_type = st.selectbox("Input Type", ["Phone", "UID"], key=f"input_type_{tab_key}")
                    list_label = f"List of {input_type}s (one per line)"
                else:
                    input_type = None
                    list_label = f"List of {config['param_name']}s (one per line)"
                items_input = st.text_area(list_label, height=100, key=f"items_{tab_key}")

            if config.get('has_message', False):
                message_input = st.text_area("Message", height=80, key=f"message_{tab_key}")

            # Timing inputs
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                item_delay = st.number_input("Item Delay (seconds)", min_value=0.0, value=5.0, step=0.1, key=f"item_delay_{tab_key}")
            with col2:
                rest_time = st.number_input("Rest Time (minutes)", min_value=0.0, value=10.0, step=0.1, key=f"rest_time_{tab_key}")
            with col3:
                rest_after = st.number_input("Rest After (items)", min_value=1, value=100, step=1, key=f"rest_after_{tab_key}")
            with col4:
                stop_after = st.number_input("Stop After (items)", min_value=1, value=5000, step=1, key=f"stop_after_{tab_key}")

            # Buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                button_text = "Get" if tab_key in ['sendmessagefriends', 'sendmessagegroups', 'sendmessagelistgroups', 'getfriends', 'getgroups', 'invitegroups'] else "Start"
                if st.button(button_text, key=f"start_{tab_key}", disabled=st.session_state.is_running[tab_key]):
                    if not selected_cookie_data:
                        st.error("Please select a cookie.")
                    elif config['has_list'] and tab_key not in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups'] and not items_input.strip():
                        st.error("Please provide input items.")
                    elif config.get('has_message', False) and not message_input.strip() and button_text != "Get":
                        st.error("Please provide a message.")
                    else:
                        st.session_state.is_running[tab_key] = True
                        process_requests(tab_key, config['param_name'], selected_cookie_data['cookie'] if selected_cookie_data else None,
                                       items_input.strip().split('\n') if config['has_list'] and tab_key not in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups'] else [''],
                                       message_input.strip() if config.get('has_message', False) else '',
                                       item_delay, rest_after, rest_time * 60, stop_after, button_text == "Get",
                                       selected_group if tab_key == 'invitegroups' else None)
            with col2:
                if st.button("Stop", key=f"stop_{tab_key}", disabled=not st.session_state.is_running[tab_key]):
                    st.session_state.is_running[tab_key] = False
                    st.success(f"Stopped {tab_key}")
            with col3:
                if st.button("Export", key=f"export_{tab_key}"):
                    export_table(tab_key, config['columns'])

            # Display results
            if st.session_state.results[tab_key]:
                df = pd.DataFrame(st.session_state.results[tab_key], columns=config['columns'])
                if config.get('has_selection', False):
                    selected_rows = st.multiselect("Select items", df.index, key=f"select_{tab_key}")
                    st.session_state.selected_items[tab_key] = set(selected_rows)
                    df['Select'] = df.index.map(lambda x: '☑' if x in selected_rows else '')
                st.dataframe(df, use_container_width=True)

def process_requests(tab_type, param_name, cookie, items, message, item_delay, rest_after, rest_time, stop_after, is_get, selected_group=None):
    stt = 0
    current_time = datetime.now().strftime('%H:%M:%S')
    current_date = datetime.now().strftime('%Y-%m-%d')
    formatted_message = message.replace('{time}', current_time).replace('{date}', current_date) if message else ''
    if tab_type in ['getfriends', 'sendmessagefriends', 'getgroups', 'sendmessagelistgroups', 'invitegroups']:
        items = ['']

    st.session_state.results[tab_type] = []

    for i, item in enumerate(items):
        if not st.session_state.is_running[tab_type]:
            st.write(f"Stopped {tab_type} processing")
            break
        if stt >= stop_after:
            st.write(f"Stopped {tab_type} after reaching {stop_after} items")
            break

        original_item = item
        input_type = st.session_state.get(f"input_type_{tab_type}", "UID") if tab_type in ['addfriend', 'sendmessages'] else None

        # Prepare API request data
        if tab_type == 'addfriend':
            data = {'cookie': cookie, 'uid' if input_type == 'UID' else 'phone': item, 'message': formatted_message}
        elif tab_type == 'sendmessages':
            data = {'cookie': cookie, 'uid' if input_type == 'UID' else 'phone': item, 'message': formatted_message}
        elif tab_type == 'checkinfo':
            data = {'cookie': cookie, 'phone': item}
        elif tab_type == 'scangroup':
            mpage = 1
            saved_group_name = 'N/A'
            while st.session_state.is_running[tab_type] and stt < stop_after:
                data = {'cookie': cookie, 'group_id': str(item), 'mpage': str(mpage)}
                try:
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    response = requests.post(API_URLS[tab_type], data=data, headers=headers)
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
                            st.session_state.results[tab_type].append(values)
                            st.write(f"{tab_type}: Member={member.get('dName')}")
                        if group_data.get('hasMoreMember') == 0:
                            break
                        mpage += 1
                        time.sleep(item_delay)
                    else:
                        break
                except Exception as e:
                    st.error(f"{tab_type} request failed: {str(e)}")
                    break
            continue
        elif tab_type == 'getfriends':
            data = {'cookie': cookie}
        elif tab_type == 'getgroups':
            data = {'cookie': cookie}
        elif tab_type == 'sendmessagefriends':
            if is_get:
                data = {'cookie': cookie}
                try:
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    response = requests.post(API_URLS['getfriends'], data=data, headers=headers)
                    result = json.loads(response.text)
                    if result.get('error_code') == 0:
                        friends = result.get('data', [])
                        for friend in friends:
                            if stt >= stop_after:
                                break
                            stt += 1
                            values = (
                                '', stt, friend.get('userId', 'N/A'), friend.get('phoneNumber', 'N/A'),
                                friend.get('displayName', 'N/A'), friend.get('zaloName', 'N/A'),
                                friend.get('sdob', 'N/A'), friend.get('status', 'N/A')[:50], 'N/A'
                            )
                            st.session_state.results[tab_type].append(values)
                        st.session_state.selected_items[tab_type].clear()
                    else:
                        st.error(f"Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Request failed: {str(e)}")
                continue
            else:
                selected_friends = [st.session_state.results[tab_type][i] for i in st.session_state.selected_items[tab_type]]
                if not selected_friends:
                    st.error("Please select at least one friend to send messages to.")
                    st.session_state.is_running[tab_type] = False
                    return
                for friend in selected_friends:
                    if not st.session_state.is_running[tab_type] or stt >= stop_after:
                        break
                    stt += 1
                    uid = friend[2]
                    name = friend[4]
                    friend_message = formatted_message.replace('{name}', name)
                    data = {'cookie': cookie, 'uid': uid, 'message': friend_message}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post(API_URLS[tab_type], data=data, headers=headers)
                        result = json.loads(response.text)
                        friend[-1] = f"✅ Success (MsgID: {result.get('msgId', 'N/A')})" if result.get('status') == 'Successfully' else f"❌ {result.get('message', 'Failed')}"
                        st.write(f"{tab_type}: {name} - {'Success' if result.get('status') == 'Successfully' else 'Failed'}")
                        time.sleep(item_delay)
                    except Exception as e:
                        friend[-1] = f"❌ {str(e)}"
                        st.error(f"{tab_type}: {name} - Failed: {str(e)}")
                    if stt % rest_after == 0 and stt < stop_after:
                        time.sleep(rest_time)
                continue
        elif tab_type == 'sendmessagegroups':
            if is_get:
                mpage = 1
                saved_group_name = 'N/A'
                while st.session_state.is_running[tab_type] and stt < stop_after:
                    data = {'cookie': cookie, 'group_id': str(item), 'mpage': str(mpage)}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post(API_URLS['scangroup'], data=data, headers=headers)
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
                                st.session_state.results[tab_type].append(values)
                            if group_data.get('hasMoreMember') == 0:
                                break
                            mpage += 1
                            time.sleep(item_delay)
                        else:
                            break
                    except Exception as e:
                        st.error(f"{tab_type} request failed: {str(e)}")
                        break
                st.session_state.selected_items[tab_type].clear()
                continue
            else:
                selected_members = [st.session_state.results[tab_type][i] for i in st.session_state.selected_items[tab_type]]
                if not selected_members:
                    st.error("No group members selected.")
                    st.session_state.is_running[tab_type] = False
                    return
                for member in selected_members:
                    if not st.session_state.is_running[tab_type] or stt >= stop_after:
                        break
                    stt += 1
                    data = {'cookie': cookie, 'uid': member[5], 'message': formatted_message.replace('{name}', member[6])}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post(API_URLS[tab_type], data=data, headers=headers)
                        result = json.loads(response.text)
                        member[-1] = f"✅ Success (MsgID: {result.get('msgId', 'N/A')})" if result.get('status') == 'Successfully' else f"❌ {result.get('message', 'Failed')}"
                        st.write(f"{tab_type}: {member[6]} - {'Success' if result.get('status') == 'Successfully' else 'Failed'}")
                        time.sleep(item_delay)
                    except Exception as e:
                        member[-1] = f"❌ {str(e)}"
                        st.error(f"{tab_type}: {member[6]} - Failed: {str(e)}")
                    if stt % rest_after == 0 and stt < stop_after:
                        time.sleep(rest_time)
                continue
        elif tab_type == 'sendmessagelistgroups':
            if is_get:
                data = {'cookie': cookie}
                try:
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    response = requests.post(API_URLS['getgroups'], data=data, headers=headers)
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
                            st.session_state.results[tab_type].append(values)
                        st.session_state.selected_items[tab_type].clear()
                    else:
                        st.error(f"Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Request failed: {str(e)}")
                continue
            else:
                selected_groups = [st.session_state.results[tab_type][i] for i in st.session_state.selected_items[tab_type]]
                if not selected_groups:
                    st.error("No groups selected.")
                    st.session_state.is_running[tab_type] = False
                    return
                for group in selected_groups:
                    if not st.session_state.is_running[tab_type] or stt >= stop_after:
                        break
                    stt += 1
                    data = {'cookie': cookie, 'group_id': group[2], 'message': formatted_message.replace('{name}', group[3])}
                    try:
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        response = requests.post(API_URLS[tab_type], data=data, headers=headers)
                        result = json.loads(response.text)
                        group[-1] = f"✅ Success (MsgID: {result.get('data', {}).get('data', {}).get('msgId', 'N/A')})" if result.get('status') == 'Success' else f"❌ {result.get('data', {}).get('error_message', 'Failed')}"
                        st.write(f"{tab_type}: {group[3]} - {'Success' if result.get('status') == 'Success' else 'Failed'}")
                        time.sleep(item_delay)
                    except Exception as e:
                        group[-1] = f"❌ {str(e)}"
                        st.error(f"{tab_type}: {group[3]} - Failed: {str(e)}")
                    if stt % rest_after == 0 and stt < stop_after:
                        time.sleep(rest_time)
                continue
        elif tab_type == 'invitegroups':
            if is_get:
                friends_data = {'cookie': cookie}
                groups_data = {'cookie': cookie}
                try:
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    friends_response = requests.post(API_URLS['getfriends'], data=friends_data, headers=headers)
                    groups_response = requests.post(API_URLS['getgroups'], data=groups_data, headers=headers)
                    friends_result = json.loads(friends_response.text)
                    groups_result = json.loads(groups_response.text)
                    if friends_result.get('error_code') == 0 and groups_result.get('error_code') == 0:
                        st.session_state.groups = groups_result.get('data', [])
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
                            st.session_state.results[tab_type].append(values)
                        st.session_state.selected_items[tab_type].clear()
                    else:
                        st.error(f"Friends Error {friends_result.get('error_code')}: {friends_result.get('error_message')} | Groups Error {groups_result.get('error_code')}: {groups_result.get('error_message')}")
                except Exception as e:
                    st.error(f"Request failed: {str(e)}")
                continue
            else:
                if not selected_group:
                    st.error("Please select a group.")
                    st.session_state.is_running[tab_type] = False
                    return
                group_id = next((g['groupId'] for g in st.session_state.groups if f"{g['name']} (ID: {g['groupId']})" == selected_group), None)
                group_name = next((g['name'] for g in st.session_state.groups if f"{g['name']} (ID: {g['groupId']})" == selected_group), 'N/A')
                if not group_id:
                    st.error("Selected group not found.")
                    st.session_state.is_running[tab_type] = False
                    return
                selected_friends = [st.session_state.results[tab_type][i] for i in st.session_state.selected_items[tab_type]]
                if not selected_friends:
                    st.error("Please select at least one friend to invite.")
                    st.session_state.is_running[tab_type] = False
                    return
                uids_list = ','.join([str(friend[2]) for friend in selected_friends])
                data = {
                    'cookie': cookie,
                    'group_id': str(group_id),
                    'uid': uids_list,
                    'message': formatted_message or 'Xin mời bạn tham gia nhóm nhé!'
                }
                batch_size = len(selected_friends)
                try:
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    response = requests.post(API_URLS[tab_type], data=data, headers=headers)
                    result = json.loads(response.text)
                    if result.get('status') == 'Success':
                        success_msg = f"✅ Batch Success ({batch_size} friends)"
                        for friend in selected_friends:
                            friend[-1] = success_msg[:50]
                        st.write(f"Invited {batch_size} friends to {group_name}")
                        stt += batch_size
                    else:
                        error_msg = result.get('error', 'Failed')
                        for friend in selected_friends:
                            friend[-1] = f"❌ {error_msg[:40]}"
                        st.error(f"Batch failed: {error_msg}")
                    time.sleep(item_delay)
                    if stt % rest_after == 0 and stt < stop_after:
                        time.sleep(rest_time)
                except Exception as e:
                    error_msg = f"Request failed: {str(e)}"
                    for friend in selected_friends:
                        friend[-1] = f"❌ {error_msg[:40]}"
                    st.error(f"Batch invite exception: {error_msg}")
                continue
        else:
            data = {'cookie': cookie, param_name: item}

        try:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(API_URLS[tab_type], data=data, headers=headers)
            result = json.loads(response.text)
            if tab_type == 'addfriend':
                stt += 1
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
                        st.session_state.results[tab_type].append(values)
                    continue
                else:
                    st.error(f"Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}")
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
                        st.session_state.results[tab_type].append(values)
                    continue
                else:
                    st.error(f"Error {result.get('error_code')}: {result.get('error_message', 'Unknown error')}")
                    continue
            st.session_state.results[tab_type].append(values)
            time.sleep(item_delay)
            if stt % rest_after == 0 and stt < stop_after:
                time.sleep(rest_time)
        except Exception as e:
            st.error(f"Request failed: {str(e)}")
            if tab_type == 'addfriend':
                stt += 1
                values = (stt, original_item, f"❌ {str(e)}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif tab_type == 'sendmessages':
                stt += 1
                values = (stt, original_item, f"❌ {str(e)}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif tab_type == 'checkinfo':
                stt += 1
                values = (stt, original_item, 'N/A', 'N/A', f"❌ {str(e)}", 'N/A', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            else:
                continue
            st.session_state.results[tab_type].append(values)

    st.session_state.is_running[tab_type] = False
    st.success(f"Completed {tab_type}")

def export_table(tab_type, columns):
    data = st.session_state.results[tab_type]
    if not data:
        st.warning("No data to export.")
        return
    df = pd.DataFrame(data, columns=columns)
    filename = f"{tab_type}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(filename, index=False)
    st.success(f"Exported {len(data)} rows to {filename}")

if __name__ == "__main__":
    main()

