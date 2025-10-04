import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import time
from datetime import datetime
import queue
import sys
import asyncio
from youtube_monitor_pubsub import YouTubeMonitorPubSub

class YouTubeMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Channel Monitor & TikTok Auto-Uploader (Ultra-Fast)")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize PubSubHubbub monitor
        self.pubsub_monitor = None
        self.monitoring = False
        self.log_queue = queue.Queue()
        self.monitor_thread = None
        self.async_loop = None
        
        # Video processing state
        self.processing_video = False
        # Upload workers for parallel processing
        self.upload_workers = []
        self.upload_worker_lock = threading.Lock()
        
        # Create GUI
        self.create_widgets()
        self.load_config()
        self.update_log()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Dashboard tab
        self.create_dashboard_tab()
        
        # Channels tab
        self.create_channels_tab()
        
        # Settings tab
        self.create_settings_tab()
        
        # Logs tab
        self.create_logs_tab()
        
    def create_dashboard_tab(self):
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="📊 Dashboard")
        
        # Status section
        status_frame = ttk.LabelFrame(dashboard_frame, text="System Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Monitoring status
        self.status_label = ttk.Label(status_frame, text="⏸️ Monitoring: Stopped", font=('Arial', 12, 'bold'))
        self.status_label.pack(anchor=tk.W)
        
        # Speed indicator
        self.speed_label = ttk.Label(status_frame, text="⚡ PubSubHubbub Mode: Real-time notifications", font=('Arial', 10, 'bold'), foreground='green')
        self.speed_label.pack(anchor=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="▶️ Start PubSubHubbub Monitoring", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.check_once_button = ttk.Button(button_frame, text="🔍 Check Once", command=self.check_once)
        self.check_once_button.pack(side=tk.LEFT, padx=5)
        
        # Performance metrics
        perf_frame = ttk.LabelFrame(status_frame, text="Performance Metrics", padding=10)
        perf_frame.pack(fill=tk.X, pady=5)
        
        # Performance grid
        perf_grid = ttk.Frame(perf_frame)
        perf_grid.pack(fill=tk.X)
        
        ttk.Label(perf_grid, text="Last Cycle Time:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.cycle_time_label = ttk.Label(perf_grid, text="0.0s", font=('Arial', 10, 'bold'))
        self.cycle_time_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(perf_grid, text="Average Cycle Time:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.avg_cycle_label = ttk.Label(perf_grid, text="0.0s", font=('Arial', 10, 'bold'))
        self.avg_cycle_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(perf_grid, text="Cache Hit Rate:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.cache_hit_label = ttk.Label(perf_grid, text="0%", font=('Arial', 10, 'bold'))
        self.cache_hit_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(perf_grid, text="Webhook URL:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.webhook_url_label = ttk.Label(perf_grid, text="Not active", font=('Arial', 10, 'bold'))
        self.webhook_url_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Statistics section
        stats_frame = ttk.LabelFrame(dashboard_frame, text="Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Stats grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        # Row 1
        ttk.Label(stats_grid, text="Active Channels:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.channels_count_label = ttk.Label(stats_grid, text="0", font=('Arial', 10, 'bold'))
        self.channels_count_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Processed Videos:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.processed_count_label = ttk.Label(stats_grid, text="0", font=('Arial', 10, 'bold'))
        self.processed_count_label.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Row 2
        ttk.Label(stats_grid, text="Server Port:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.port_label = ttk.Label(stats_grid, text="8080", font=('Arial', 10, 'bold'))
        self.port_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(stats_grid, text="Last Notification:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.last_notification_label = ttk.Label(stats_grid, text="Never", font=('Arial', 10, 'bold'))
        self.last_notification_label.grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Recent activity
        activity_frame = ttk.LabelFrame(dashboard_frame, text="Recent Activity", padding=10)
        activity_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.activity_text = scrolledtext.ScrolledText(activity_frame, height=15, font=('Consolas', 9))
        self.activity_text.pack(fill=tk.BOTH, expand=True)
        
    def create_channels_tab(self):
        channels_frame = ttk.Frame(self.notebook)
        self.notebook.add(channels_frame, text="📺 Channels")
        
        # Channel list
        list_frame = ttk.LabelFrame(channels_frame, text="Configured Channels", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for channels
        columns = ('Name', 'Channel ID', 'TikTok Cookie', 'Proxy', 'Status')
        self.channels_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.channels_tree.heading(col, text=col)
            if col == 'Proxy':
                self.channels_tree.column(col, width=120)
            else:
                self.channels_tree.column(col, width=150)
        
        self.channels_tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.channels_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.channels_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = ttk.Frame(channels_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="➕ Add Channel", command=self.add_channel_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✏️ Edit Channel", command=self.edit_channel).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🗑️ Remove Channel", command=self.remove_channel).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🔄 Refresh", command=self.refresh_channels).pack(side=tk.LEFT, padx=5)
        
    def create_settings_tab(self):
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Settings")
        
        # Settings form
        form_frame = ttk.LabelFrame(settings_frame, text="Configuration", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Server port
        ttk.Label(form_frame, text="Server Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_var = tk.StringVar(value="8080")
        self.port_entry = ttk.Entry(form_frame, textvariable=self.port_var, width=10)
        self.port_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Download path
        ttk.Label(form_frame, text="Download Path:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        path_frame = ttk.Frame(form_frame)
        path_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.download_path_var = tk.StringVar(value="VideosDirPath")
        self.path_entry = ttk.Entry(path_frame, textvariable=self.download_path_var, width=40)
        self.path_entry.pack(side=tk.LEFT)
        
        ttk.Button(path_frame, text="Browse", command=self.browse_download_path).pack(side=tk.LEFT, padx=5)
        
        # Auto upload
        self.auto_upload_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form_frame, text="Auto Upload to TikTok", variable=self.auto_upload_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Use ngrok
        self.use_ngrok_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(form_frame, text="Use ngrok tunnel", variable=self.use_ngrok_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # ngrok URL
        ttk.Label(form_frame, text="ngrok URL (optional):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.ngrok_url_var = tk.StringVar()
        self.ngrok_url_entry = ttk.Entry(form_frame, textvariable=self.ngrok_url_var, width=40)
        self.ngrok_url_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Save button
        ttk.Button(form_frame, text="💾 Save Settings", command=self.save_settings).grid(row=5, column=0, columnspan=2, pady=10)
        
        # TikTok accounts section
        accounts_frame = ttk.LabelFrame(settings_frame, text="TikTok Accounts", padding=10)
        accounts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Account list
        self.accounts_tree = ttk.Treeview(accounts_frame, columns=('Name', 'Status', 'Session Info'), show='headings', height=5)
        self.accounts_tree.heading('Name', text='Account Name')
        self.accounts_tree.heading('Status', text='Status')
        self.accounts_tree.heading('Session Info', text='Session Information')
        self.accounts_tree.column('Name', width=150)
        self.accounts_tree.column('Status', width=100)
        self.accounts_tree.column('Session Info', width=300)
        self.accounts_tree.pack(fill=tk.X)
        
        # Account buttons
        account_button_frame = ttk.Frame(accounts_frame)
        account_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(account_button_frame, text="🔑 Login Account", command=self.login_tiktok_account).pack(side=tk.LEFT, padx=5)
        ttk.Button(account_button_frame, text="🔄 Refresh Status", command=self.refresh_accounts).pack(side=tk.LEFT, padx=5)
        
        # Proxy management section
        proxy_frame = ttk.LabelFrame(settings_frame, text="Proxy Management", padding=10)
        proxy_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Proxy list
        self.proxy_tree = ttk.Treeview(proxy_frame, columns=('IP:Port', 'Username', 'Password', 'Status'), show='headings', height=5)
        self.proxy_tree.heading('IP:Port', text='IP:Port')
        self.proxy_tree.heading('Username', text='Username')
        self.proxy_tree.heading('Password', text='Password')
        self.proxy_tree.heading('Status', text='Status')
        self.proxy_tree.column('IP:Port', width=150)
        self.proxy_tree.column('Username', width=120)
        self.proxy_tree.column('Password', width=120)
        self.proxy_tree.column('Status', width=100)
        self.proxy_tree.pack(fill=tk.X)
        
        # Proxy buttons
        proxy_button_frame = ttk.Frame(proxy_frame)
        proxy_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(proxy_button_frame, text="➕ Add Proxy", command=self.add_proxy_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_button_frame, text="✏️ Edit Proxy", command=self.edit_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_button_frame, text="🗑️ Remove Proxy", command=self.remove_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_button_frame, text="📁 Import from File", command=self.import_proxies).pack(side=tk.LEFT, padx=5)
        ttk.Button(proxy_button_frame, text="🔄 Refresh", command=self.refresh_proxies).pack(side=tk.LEFT, padx=5)
        
    def create_logs_tab(self):
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="📋 Logs")
        
        # Log controls
        controls_frame = ttk.Frame(logs_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(controls_frame, text="🗑️ Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="💾 Save Logs", command=self.save_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="🔄 Auto-scroll", command=self.toggle_auto_scroll).pack(side=tk.LEFT, padx=5)
        
        # Log level filter
        ttk.Label(controls_frame, text="Log Level:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level_var = tk.StringVar(value="All")
        log_level_combo = ttk.Combobox(controls_frame, textvariable=self.log_level_var, values=["All", "Info", "Warning", "Error"], width=10)
        log_level_combo.pack(side=tk.LEFT, padx=5)
        
        # Log display
        log_frame = ttk.LabelFrame(logs_frame, text="System Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas', 9), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for different log levels
        self.log_text.tag_configure("info", foreground="black")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("success", foreground="green")
        
    def load_config(self):
        try:
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                # Update settings
                self.port_var.set(str(config.get("pubsub_port", 8080)))
                self.download_path_var.set(config.get("download_path", "VideosDirPath"))
                self.auto_upload_var.set(config.get("auto_upload", True))
                self.use_ngrok_var.set(config.get("use_ngrok", True))
                self.ngrok_url_var.set(config.get("ngrok_url", ""))
                
                # Update statistics
                self.update_statistics()
                self.refresh_channels()
                self.refresh_accounts()
                self.refresh_proxies()
                
        except Exception as e:
            self.log_message(f"Error loading config: {e}", "error")
    
    def update_statistics(self):
        try:
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                channels_count = len(config.get("channels", []))
                self.channels_count_label.config(text=str(channels_count))
                
                # Load processed videos count
                processed_file = config.get("processed_videos_file", "processed_videos.json")
                if os.path.exists(processed_file):
                    with open(processed_file, 'r') as f:
                        processed_videos = json.load(f)
                    self.processed_count_label.config(text=str(len(processed_videos)))
                else:
                    self.processed_count_label.config(text="0")
                
                self.port_label.config(text=str(config.get('pubsub_port', 8080)))
                
        except Exception as e:
            self.log_message(f"Error updating statistics: {e}", "error")
    
    def refresh_channels(self):
        # Clear existing items
        for item in self.channels_tree.get_children():
            self.channels_tree.delete(item)
        
        try:
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                for channel in config.get("channels", []):
                    name = channel.get("name", "Unknown")
                    channel_id = channel.get("channel_id", "N/A")
                    tiktok_cookie = channel.get("tiktok_cookie", "default")
                    
                    # Get proxy information
                    proxy_info = channel.get("proxy")
                    if proxy_info:
                        proxy_display = f"{proxy_info['ip']}:{proxy_info['port']}"
                    else:
                        proxy_display = "No Proxy"
                    
                    # Check if TikTok cookie exists
                    cookie_file = f"tiktok_session-{tiktok_cookie}"
                    status = "✅ Active" if os.path.exists(f"CookiesDir/{cookie_file}") else "❌ No Login"
                    
                    self.channels_tree.insert('', 'end', values=(name, channel_id, tiktok_cookie, proxy_display, status))
                    
        except Exception as e:
            self.log_message(f"Error refreshing channels: {e}", "error")
    
    def refresh_accounts(self):
        # Clear existing items
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        
        try:
            # Ensure CookiesDir exists
            cookies_dir = "CookiesDir"
            if not os.path.exists(cookies_dir):
                os.makedirs(cookies_dir, exist_ok=True)
                self.log_message("📁 Created CookiesDir directory", "info")
            
            if os.path.exists("CookiesDir"):
                accounts_found = False
                for file in os.listdir("CookiesDir"):
                    if file.startswith("tiktok_session-"):
                        account_name = file.replace("tiktok_session-", "")
                        accounts_found = True
                        
                        # Check if the cookie file is valid
                        try:
                            from tiktok_uploader.cookies import load_cookies_from_file
                            cookies = load_cookies_from_file(f"tiktok_session-{account_name}")
                            session_cookie = next((c for c in cookies if c["name"] == 'sessionid'), None)
                            dc_cookie = next((c for c in cookies if c["name"] == 'tt-target-idc'), None)
                            
                            if session_cookie and dc_cookie:
                                status = "✅ Valid Session"
                                session_info = f"Session: {session_cookie['value'][:10]}... | DC: {dc_cookie['value']}"
                            elif session_cookie:
                                status = "⚠️ Partial Session"
                                session_info = f"Session: {session_cookie['value'][:10]}... | DC: Missing"
                            else:
                                status = "❌ Invalid Session"
                                session_info = "No valid session found"
                                
                        except Exception as e:
                            status = "❌ Error Loading"
                            session_info = f"Error: {str(e)[:30]}..."
                        
                        self.accounts_tree.insert('', 'end', values=(account_name, status, session_info))
                
                if not accounts_found:
                    self.accounts_tree.insert('', 'end', values=("No accounts found", "❌ Not Logged In", "Use 'Login Account' to add TikTok accounts"))
            else:
                self.accounts_tree.insert('', 'end', values=("CookiesDir not found", "❌ Directory Missing", "Create CookiesDir folder and try again"))
                
        except Exception as e:
            self.log_message(f"Error refreshing accounts: {e}", "error")
            self.accounts_tree.insert('', 'end', values=("Error", "❌ Failed to Load", f"Error: {str(e)[:30]}..."))
    
    def add_channel_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Channel")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Form
        ttk.Label(dialog, text="Channel Name:").pack(pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Channel ID:").pack(pady=5)
        channel_id_var = tk.StringVar()
        channel_id_entry = ttk.Entry(dialog, textvariable=channel_id_var, width=40)
        channel_id_entry.pack(pady=5)
        
        ttk.Label(dialog, text="TikTok Cookie Name:").pack(pady=5)
        cookie_var = tk.StringVar()
        cookie_entry = ttk.Entry(dialog, textvariable=cookie_var, width=40)
        cookie_entry.pack(pady=5)
        
        # Proxy selection
        ttk.Label(dialog, text="Proxy (optional):").pack(pady=5)
        proxy_var = tk.StringVar(value="No Proxy")
        proxy_combo = ttk.Combobox(dialog, textvariable=proxy_var, width=40, state="readonly")
        proxy_combo.pack(pady=5)
        
        # Load available proxies
        def load_proxy_options():
            proxy_options = ["No Proxy"]
            try:
                if os.path.exists("monitor_config.json"):
                    with open("monitor_config.json", 'r') as f:
                        config = json.load(f)
                    
                    for proxy in config.get("proxies", []):
                        proxy_options.append(f"{proxy['ip']}:{proxy['port']}")
                    
            except Exception as e:
                self.log_message(f"Error loading proxies: {e}", "error")
            
            proxy_combo['values'] = proxy_options
        
        load_proxy_options()
        
        def save_channel():
            name = name_var.get().strip()
            channel_id = channel_id_var.get().strip()
            cookie = cookie_var.get().strip()
            proxy = proxy_var.get().strip()
            
            if not name or not channel_id:
                messagebox.showerror("Error", "Please fill in all required fields")
                return
            
            if not cookie:
                cookie = "default"
            
            # Handle proxy selection
            if proxy == "No Proxy":
                proxy = None
            else:
                # Extract proxy details from selection
                try:
                    if os.path.exists("monitor_config.json"):
                        with open("monitor_config.json", 'r') as f:
                            config = json.load(f)
                        
                        for p in config.get("proxies", []):
                            if f"{p['ip']}:{p['port']}" == proxy:
                                proxy = {
                                    "ip": p['ip'],
                                    "port": p['port'],
                                    "username": p['username'],
                                    "password": p['password']
                                }
                                break
                except Exception as e:
                    self.log_message(f"Error processing proxy selection: {e}", "error")
                    proxy = None
            
            try:
                # Load existing config
                if os.path.exists("monitor_config.json"):
                    with open("monitor_config.json", 'r') as f:
                        config = json.load(f)
                else:
                    config = {"channels": [], "check_interval_seconds": 1, "auto_upload": True, "download_path": "VideosDirPath"}
                
                # Add new channel
                channel_data = {
                    "name": name,
                    "channel_id": channel_id,
                    "tiktok_cookie": cookie
                }
                
                if proxy:
                    channel_data["proxy"] = proxy
                
                config["channels"].append(channel_data)
                
                # Save config
                with open("monitor_config.json", 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.log_message(f"Added channel: {name}", "success")
                self.refresh_channels()
                self.update_statistics()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add channel: {e}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Save", command=save_channel).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def edit_channel(self):
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to edit")
            return
        
        # Get selected channel
        item = self.channels_tree.item(selection[0])
        values = item['values']
        
        # Extract current values
        current_name = values[0]
        current_channel_id = values[1]
        current_cookie = values[2]
        
        # Get current proxy from config
        self.current_channel_proxy = None
        try:
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                for channel in config.get("channels", []):
                    if channel["name"] == current_name:
                        self.current_channel_proxy = channel.get("proxy")
                        break
        except Exception as e:
            self.log_message(f"Error loading channel proxy: {e}", "error")
        
        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Channel")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()  # Make dialog focused
        
        # Form
        ttk.Label(dialog, text="Channel Name:").pack(pady=5)
        name_var = tk.StringVar(value=current_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.focus_set()  # Set focus to first field
        
        ttk.Label(dialog, text="Channel ID:").pack(pady=5)
        channel_id_var = tk.StringVar(value=current_channel_id)
        channel_id_entry = ttk.Entry(dialog, textvariable=channel_id_var, width=40)
        channel_id_entry.pack(pady=5)
        
        ttk.Label(dialog, text="TikTok Cookie Name:").pack(pady=5)
        cookie_var = tk.StringVar(value=current_cookie)
        cookie_entry = ttk.Entry(dialog, textvariable=cookie_var, width=40)
        cookie_entry.pack(pady=5)
        
        # Proxy selection
        ttk.Label(dialog, text="Proxy (optional):").pack(pady=5)
        proxy_var = tk.StringVar(value="No Proxy")
        proxy_combo = ttk.Combobox(dialog, textvariable=proxy_var, width=40, state="readonly")
        proxy_combo.pack(pady=5)
        
        # Load available proxies and set current selection
        def load_proxy_options():
            proxy_options = ["No Proxy"]
            try:
                if os.path.exists("monitor_config.json"):
                    with open("monitor_config.json", 'r') as f:
                        config = json.load(f)
                    
                    for proxy in config.get("proxies", []):
                        proxy_options.append(f"{proxy['ip']}:{proxy['port']}")
                    
                    # Set current proxy selection if exists
                    if hasattr(self, 'current_channel_proxy'):
                        current_proxy_str = f"{self.current_channel_proxy['ip']}:{self.current_channel_proxy['port']}"
                        if current_proxy_str in proxy_options:
                            proxy_var.set(current_proxy_str)
                    
            except Exception as e:
                self.log_message(f"Error loading proxies: {e}", "error")
            
            proxy_combo['values'] = proxy_options
        
        load_proxy_options()
        
        def save_channel():
            name = name_var.get().strip()
            channel_id = channel_id_var.get().strip()
            cookie = cookie_var.get().strip()
            proxy = proxy_var.get().strip()
            
            if not name or not channel_id:
                messagebox.showerror("Error", "Please fill in all required fields")
                return
            
            if not cookie:
                cookie = "default"
            
            # Handle proxy selection
            if proxy == "No Proxy":
                proxy = None
            else:
                # Extract proxy details from selection
                try:
                    if os.path.exists("monitor_config.json"):
                        with open("monitor_config.json", 'r') as f:
                            config = json.load(f)
                        
                        for p in config.get("proxies", []):
                            if f"{p['ip']}:{p['port']}" == proxy:
                                proxy = {
                                    "ip": p['ip'],
                                    "port": p['port'],
                                    "username": p['username'],
                                    "password": p['password']
                                }
                                break
                except Exception as e:
                    self.log_message(f"Error processing proxy selection: {e}", "error")
                    proxy = None
            
            try:
                # Load existing config
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                # Find and update the channel
                for channel in config["channels"]:
                    if channel["name"] == current_name:
                        channel["name"] = name
                        channel["channel_id"] = channel_id
                        channel["tiktok_cookie"] = cookie
                        
                        # Update proxy
                        if proxy:
                            channel["proxy"] = proxy
                        elif "proxy" in channel:
                            del channel["proxy"]
                        
                        break
                
                # Save config
                with open("monitor_config.json", 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.log_message(f"Updated channel: {name}", "success")
                self.refresh_channels()
                self.update_statistics()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update channel: {e}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Save", command=save_channel).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def remove_channel(self):
        selection = self.channels_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a channel to remove")
            return
        
        item = self.channels_tree.item(selection[0])
        channel_name = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove channel '{channel_name}'?"):
            try:
                # Load config
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                # Remove channel
                config["channels"] = [ch for ch in config["channels"] if ch["name"] != channel_name]
                
                # Save config
                with open("monitor_config.json", 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.log_message(f"Removed channel: {channel_name}", "success")
                self.refresh_channels()
                self.update_statistics()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove channel: {e}")
    
    def save_settings(self):
        try:
            # Load existing config
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
            else:
                config = {"channels": []}
            
            # Update settings
            config["pubsub_port"] = int(self.port_var.get())
            config["download_path"] = self.download_path_var.get()
            config["auto_upload"] = self.auto_upload_var.get()
            config["use_ngrok"] = self.use_ngrok_var.get()
            config["ngrok_url"] = self.ngrok_url_var.get()
            
            # Preserve existing proxies
            if "proxies" not in config:
                config["proxies"] = []
            
            # Save config
            with open("monitor_config.json", 'w') as f:
                json.dump(config, f, indent=4)
            
            self.log_message("Settings saved successfully", "success")
            self.update_statistics()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def browse_download_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_path_var.set(path)
    
    def login_tiktok_account(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Login TikTok Account")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (250 // 2)
        dialog.geometry(f"400x250+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔐 TikTok Account Login", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Instructions
        instructions = ttk.Label(main_frame, text="Enter a name to save this TikTok account.\nThis will be used to identify the account in the system.", 
                                wraplength=350, justify=tk.CENTER)
        instructions.pack(pady=(0, 15))
        
        # Account name input
        ttk.Label(main_frame, text="Account Name:").pack(anchor=tk.W, pady=(0, 5))
        account_var = tk.StringVar()
        account_entry = ttk.Entry(main_frame, textvariable=account_var, width=40)
        account_entry.pack(fill=tk.X, pady=(0, 15))
        account_entry.focus()
        
        # Validation function
        def validate_account_name():
            account_name = account_var.get().strip()
            if not account_name:
                messagebox.showerror("Error", "Please enter an account name")
                return False
            
            # Check for invalid characters
            invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
            for char in invalid_chars:
                if char in account_name:
                    messagebox.showerror("Error", f"Account name cannot contain: {char}")
                    return False
            
            # Check if account already exists
            cookie_file = f"CookiesDir/tiktok_session-{account_name}"
            if os.path.exists(cookie_file):
                result = messagebox.askyesno("Account Exists", 
                    f"Account '{account_name}' already exists.\nDo you want to overwrite it?")
                if not result:
                    return False
            
            return True
        
        def start_login():
            if not validate_account_name():
                return
            
            account_name = account_var.get().strip()
            dialog.destroy()
            
            # Start login process in separate thread
            def login_thread():
                try:
                    self.log_message(f"🔐 Starting TikTok login for account: {account_name}", "info")
                    self.log_message("🌐 Opening browser window for manual login...", "info")
                    self.log_message("📝 Please login to your TikTok account in the browser window", "info")
                    self.log_message("⏱️ You have 5 minutes to complete the login process", "info")
                    self.log_message("🔒 The browser will close automatically after successful login", "info")
                    
                    # Ensure CookiesDir exists
                    cookies_dir = "CookiesDir"
                    if not os.path.exists(cookies_dir):
                        os.makedirs(cookies_dir, exist_ok=True)
                        self.log_message(f"📁 Created CookiesDir directory", "info")
                    
                    # Import and run the login function (same as CLI)
                    try:
                        from tiktok_uploader import tiktok
                        self.log_message("✅ Successfully imported tiktok_uploader module", "info")
                    except ImportError as import_error:
                        self.log_message(f"❌ Failed to import tiktok_uploader: {import_error}", "error")
                        messagebox.showerror("Import Error", 
                            f"Failed to import TikTok uploader module:\n\n{import_error}\n\n"
                            f"This might be a build issue. Please check the logs.")
                        return
                    
                    # Check if we're running in an executable
                    if getattr(sys, 'frozen', False):
                        self.log_message("🔧 Running in executable mode", "info")
                        # In executable mode, we might need to handle paths differently
                        base_path = os.path.dirname(sys.executable)
                        self.log_message(f"📂 Base path: {base_path}", "info")
                    
                    session_id = tiktok.login(account_name)
                    
                    if session_id:
                        self.log_message(f"✅ Successfully logged in to TikTok account: {account_name}", "success")
                        self.log_message(f"🔑 Session ID: {session_id[:10]}...", "success")
                        self.log_message(f"💾 Account saved as: tiktok_session-{account_name}", "success")
                        
                        # Show success message
                        messagebox.showinfo("Login Successful", 
                            f"Successfully logged in to TikTok account: {account_name}\n\n"
                            f"Account saved and ready to use for uploads.")
                    else:
                        self.log_message(f"❌ Login failed for account: {account_name}", "error")
                        messagebox.showerror("Login Failed", 
                            f"Failed to login to TikTok account: {account_name}\n\n"
                            f"Please try again.")
                    
                    self.refresh_accounts()
                    
                except Exception as e:
                    error_msg = f"Failed to login to TikTok account {account_name}: {e}"
                    self.log_message(error_msg, "error")
                    import traceback
                    self.log_message(f"Error details: {traceback.format_exc()}", "error")
                    
                    # Provide more specific error messages for common issues
                    if "Chrome" in str(e) or "browser" in str(e).lower():
                        error_help = "\n\n💡 Make sure Chrome browser is installed and accessible."
                    elif "import" in str(e).lower():
                        error_help = "\n\n💡 This might be a build issue. Try running the script directly instead of the executable."
                    elif "path" in str(e).lower() or "file" in str(e).lower():
                        error_help = "\n\n💡 Check if the application has permission to create files in the current directory."
                    else:
                        error_help = "\n\n💡 Please check the logs for more details."
                    
                    messagebox.showerror("Login Error", 
                        f"An error occurred during login:\n\n{error_msg}{error_help}")
            
            threading.Thread(target=login_thread, daemon=True).start()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Start Login button
        login_button = ttk.Button(button_frame, text="🔐 Start Login", command=start_login, style="Accent.TButton")
        login_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT)
        
        # Bind Enter key to start login
        dialog.bind('<Return>', lambda e: start_login())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def start_monitoring(self):
        if self.monitoring:
            return
        
        try:
            # Initialize PubSubHubbub monitor
            self.pubsub_monitor = YouTubeMonitorPubSub(log_callback=self.log_message)
            self.monitoring = True
            
            # Update UI
            self.status_label.config(text="▶️ Monitoring: Starting PubSubHubbub...")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Start monitoring in separate thread with asyncio
            def monitoring_thread():
                try:
                    # Create new event loop for this thread
                    self.async_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.async_loop)
                    
                    # Start the PubSubHubbub monitoring
                    self.async_loop.run_until_complete(self.pubsub_monitor.start_monitoring())
                    
                except Exception as e:
                    self.log_message(f"Monitoring error: {e}", "error")
                    self.stop_monitoring()
            
            self.monitor_thread = threading.Thread(target=monitoring_thread, daemon=True)
            self.monitor_thread.start()
            
            # Update status after a short delay
            self.root.after(2000, self.update_monitoring_status)
            
            self.log_message("🚀 Starting PubSubHubbub monitoring...", "info")
            self.log_message("📡 Setting up webhook server and subscriptions...", "info")
            
        except Exception as e:
            self.log_message(f"Failed to start monitoring: {e}", "error")
            self.stop_monitoring()
    
    def update_monitoring_status(self):
        """Update monitoring status after startup."""
        if self.monitoring and self.pubsub_monitor:
            try:
                # Check if the monitor is running
                if hasattr(self.pubsub_monitor, 'is_running') and self.pubsub_monitor.is_running():
                    status = self.pubsub_monitor.get_status()
                    
                    self.status_label.config(text="▶️ Monitoring: Running (PubSubHubbub)")
                    self.webhook_url_label.config(text=status['webhook_url'] or "Active")
                    self.last_notification_label.config(text=status['stats'].get('last_notification', 'Never'))
                    
                    self.log_message("✅ PubSubHubbub monitoring started successfully!", "success")
                    self.log_message(f"📡 Webhook URL: {status['webhook_url']}", "info")
                    self.log_message(f"📊 Active subscriptions: {status['subscriptions']}", "info")
                else:
                    self.status_label.config(text="⏸️ Monitoring: Starting...")
                    # Retry after 2 seconds
                    self.root.after(2000, self.update_monitoring_status)
                    
            except Exception as e:
                self.log_message(f"Error updating status: {e}", "error")
                # If there's an error, try to restart monitoring
                self.log_message("Attempting to restart monitoring...", "warning")
                self.root.after(2000, self.update_monitoring_status)
    
    def stop_monitoring(self):
        if not self.monitoring:
            return
        
        self.monitoring = False
        
        # Stop PubSubHubbub server if running
        if self.pubsub_monitor and self.async_loop:
            try:
                # Schedule stop in the async loop
                future = asyncio.run_coroutine_threadsafe(
                    self.pubsub_monitor.stop_monitoring(), 
                    self.async_loop
                )
                future.result(timeout=5)
            except Exception as e:
                self.log_message(f"Error stopping PubSubHubbub server: {e}", "error")
        
        # Wait for thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        # Update UI
        self.status_label.config(text="⏸️ Monitoring: Stopped")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        self.log_message("⏹️ Stopped PubSubHubbub monitoring", "info")
        
    def cleanup(self):
        """Clean up resources before closing"""
        # Stop monitoring
        self.stop_monitoring()
        
        # Wait for upload workers to finish
        with self.upload_worker_lock:
            for worker in self.upload_workers:
                if worker.is_alive():
                    worker.join(timeout=1)
    
    def check_once(self):
        try:
            self.log_message("🔍 PubSubHubbub doesn't support manual checks - it's real-time only!", "warning")
            self.log_message("📡 The system automatically receives notifications when new videos are published", "info")
            self.log_message("⚡ No polling needed - instant notifications via webhooks", "info")
            
        except Exception as e:
            self.log_message(f"Check failed: {e}", "error")
    
    def get_active_channels(self):
        """Get active channels from config"""
        try:
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                return config.get("channels", [])
            return []
        except Exception as e:
            self.log_message(f"Error loading channels: {e}", "error")
            return []
    
    def update_performance_metrics(self, cycle_time, avg_cycle):
        """Update performance metrics in UI"""
        self.cycle_time_label.config(text=f"{cycle_time:.1f}s")
        self.avg_cycle_label.config(text=f"{avg_cycle:.1f}s")
        
        # Color code based on performance
        if cycle_time < 5:
            self.cycle_time_label.config(foreground='green')
        elif cycle_time < 10:
            self.cycle_time_label.config(foreground='orange')
        else:
            self.cycle_time_label.config(foreground='red')
    
    def log_message(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Add to queue for thread-safe logging
        self.log_queue.put((formatted_message, level))
        
        # Also add to activity text
        self.activity_text.insert(tk.END, formatted_message)
        self.activity_text.see(tk.END)
    
    def update_log(self):
        # Process queued log messages
        try:
            while True:
                message, level = self.log_queue.get_nowait()
                
                # Add to log text with appropriate tag
                self.log_text.insert(tk.END, message, level)
                self.log_text.see(tk.END)
                
                # Limit log size
                if self.log_text.index(tk.END).split('.')[0] > '1000':
                    self.log_text.delete('1.0', '100.0')
                
        except queue.Empty:
            pass
        
        # Update last notification time
        if self.monitoring and self.pubsub_monitor:
            try:
                if hasattr(self.pubsub_monitor, 'is_running') and self.pubsub_monitor.is_running():
                    status = self.pubsub_monitor.get_status()
                    last_notification = status['stats'].get('last_notification')
                    if last_notification:
                        # Convert ISO format to readable time
                        try:
                            dt = datetime.fromisoformat(last_notification.replace('Z', '+00:00'))
                            self.last_notification_label.config(text=dt.strftime("%H:%M:%S"))
                        except:
                            self.last_notification_label.config(text="Recent")
            except:
                pass
        
        # Schedule next update
        self.root.after(100, self.update_log)
    
    def clear_logs(self):
        self.log_text.delete('1.0', tk.END)
        self.activity_text.delete('1.0', tk.END)
        self.log_message("Logs cleared", "info")
    
    def save_logs(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get('1.0', tk.END))
                self.log_message(f"Logs saved to {filename}", "success")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")
    
    def toggle_auto_scroll(self):
        # Implementation for auto-scroll toggle
        pass
    
    def process_video_immediately(self, video, channel):
        """Process video immediately step by step"""
        if self.processing_video:
            self.log_message(f"⏳ Already processing a video, skipping: {video['title']}", "warning")
            return
        
        self.processing_video = True
        
        try:
            title = video['title']
            self.log_message(f"🚀 Starting immediate processing for: {title}", "info")
            
            # Initialize YouTubeMonitor if needed
            if not hasattr(self, 'yt_monitor'):
                with threading.Lock():
                    if not hasattr(self, 'yt_monitor'):
                        from youtube_monitor import YouTubeMonitor
                        self.yt_monitor = YouTubeMonitor(log_callback=self.log_message)
            
            # Get the video URL, cookie, and proxy
            video_url = video['url']
            tiktok_cookie = channel.get("tiktok_cookie", "default")
            proxy_config = channel.get("proxy")
            
            # Configure proxy if available
            if proxy_config and hasattr(self, 'yt_monitor'):
                try:
                    # Use the comprehensive proxy configuration method
                    proxy_success = self.configure_youtube_monitor_proxy(self.yt_monitor, proxy_config)
                    
                    if proxy_success:
                        self.log_message(f"🌐 Proxy successfully configured: {proxy_config['ip']}:{proxy_config['port']}", "success")
                    else:
                        self.log_message(f"⚠️ Proxy configuration failed, using fallback methods", "warning")
                        
                except Exception as e:
                    self.log_message(f"⚠️ Failed to configure proxy: {e}", "warning")
                    # Clear proxy environment variables on error
                    self.clear_proxy_environment()
            else:
                # Clear any existing proxy environment variables
                self.clear_proxy_environment()
            
            # Step 1: Download the video
            self.log_message(f"📥 Step 1: Downloading video...", "info")
            output_path = os.path.join(
                os.path.abspath(self.yt_monitor.config["download_path"]), 
                f"new_video_{video['id']}.mp4"
            )
            
            downloaded_path = self.yt_monitor.download_video(video_url, output_path)
            if not downloaded_path:
                self.log_message(f"❌ Failed to download video: {title}", "error")
                return
            
            self.log_message(f"✅ Step 1 completed: Video downloaded successfully", "success")
            
            # Step 2: Split the video into 5 parts (with immediate upload and duration processing)
            self.log_message(f"✂️ Step 2: Processing video duration and splitting into 5 parts...", "info")
            
            # Store proxy config for use in upload workers
            self.current_proxy_config = proxy_config
            
            # Call split_video with proxy configuration
            split_videos = self.yt_monitor.split_video(downloaded_path, 5, title, tiktok_cookie, "Unknown", proxy_config)
            if not split_videos:
                self.log_message(f"❌ Failed to split video: {title}", "error")
                try:
                    os.remove(downloaded_path)
                except:
                    pass
                return
            
            self.log_message(f"✅ Step 2 completed: Video split and uploads initiated", "success")
            
            # Step 3: Uploads are now handled automatically in split_video function
            self.log_message(f"📤 Step 3: Uploads completed automatically during splitting", "info")
            
            # Step 4: Cleanup
            self.log_message(f"🧹 Step 4: Cleaning up temporary files...", "info")
            # Clean up the original downloaded file
            try:
                os.remove(downloaded_path)
            except:
                pass
            
            self.log_message(f"✅ Step 4 completed: Cleanup finished", "success")
            
            # Final summary
            self.log_message(f"🎉 Video processing completed: All parts processed and uploaded", "success")
            
            # Mark as processed (now handled by PubSubHubbub server)
            if self.pubsub_monitor:
                self.pubsub_monitor.processed_videos.add(video['id'])
                self.pubsub_monitor.save_processed_videos()
            
        except Exception as e:
            self.log_message(f"❌ Error processing video {video.get('title', 'unknown')}: {str(e)}", "error")
            import traceback
            self.log_message(f"Error details: {traceback.format_exc()}", "error")
        
        finally:
            self.processing_video = False
    
    def upload_part_worker(self, part_path, part_title, tiktok_cookie, part_num, total_parts, original_title, proxy_config=None):
        """Worker thread to upload a single video part immediately"""
        try:
            self.log_message(f"📤 Worker {part_num}: Starting upload for part {part_num}/{total_parts}...", "info")
            
            # Configure proxy if available
            if proxy_config and hasattr(self, 'yt_monitor'):
                try:
                    # Use the comprehensive proxy configuration method
                    proxy_success = self.configure_youtube_monitor_proxy(self.yt_monitor, proxy_config)
                    
                    if proxy_success:
                        self.log_message(f"🌐 Worker {part_num}: Proxy successfully configured: {proxy_config['ip']}:{proxy_config['port']}", "success")
                    else:
                        self.log_message(f"⚠️ Worker {part_num}: Proxy configuration failed, using fallback methods", "warning")
                        
                except Exception as e:
                    self.log_message(f"⚠️ Worker {part_num}: Failed to configure proxy: {e}", "warning")
                    # Clear proxy environment variables on error
                    self.clear_proxy_worker(part_num)
            else:
                # Clear any existing proxy environment variables
                self.clear_proxy_worker(part_num)
            
            # Upload the part immediately with proxy configuration
            success = self.yt_monitor.upload_to_tiktok(part_path, part_title, tiktok_cookie, proxy_config)
            
            if success:
                self.log_message(f"✅ Worker {part_num}: Successfully uploaded part {part_num} of {original_title}", "success")
                # Clean up the part file immediately after successful upload
                try:
                    os.remove(part_path)
                    self.log_message(f"🧹 Worker {part_num}: Cleaned up part file", "info")
                except Exception as e:
                    self.log_message(f"⚠️ Worker {part_num}: Failed to clean up part file: {e}", "warning")
            else:
                self.log_message(f"❌ Worker {part_num}: Failed to upload part {part_num} of {original_title}", "error")
                # Keep the file for potential retry or manual upload
                self.log_message(f"💾 Worker {part_num}: Keeping part file for potential retry", "info")
                
        except Exception as e:
            self.log_message(f"❌ Worker {part_num}: Error uploading part {part_num}: {str(e)}", "error")
            import traceback
            self.log_message(f"Worker {part_num} error details: {traceback.format_exc()}", "error")
    
    # Proxy Management Methods
    def add_proxy_dialog(self):
        """Dialog to add a new proxy"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Proxy")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Form
        ttk.Label(dialog, text="IP Address:").pack(pady=5)
        ip_var = tk.StringVar()
        ip_entry = ttk.Entry(dialog, textvariable=ip_var, width=40)
        ip_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Port:").pack(pady=5)
        port_var = tk.StringVar()
        port_entry = ttk.Entry(dialog, textvariable=port_var, width=40)
        port_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Username:").pack(pady=5)
        username_var = tk.StringVar()
        username_entry = ttk.Entry(dialog, textvariable=username_var, width=40)
        username_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Password:").pack(pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(dialog, textvariable=password_var, width=40, show="*")
        password_entry.pack(pady=5)
        
        def save_proxy():
            ip = ip_var.get().strip()
            port = port_var.get().strip()
            username = username_var.get().strip()
            password = password_var.get().strip()
            
            if not all([ip, port, username, password]):
                messagebox.showerror("Error", "Please fill in all fields")
                return
            
            try:
                # Load existing config
                if os.path.exists("monitor_config.json"):
                    with open("monitor_config.json", 'r') as f:
                        config = json.load(f)
                else:
                    config = {"channels": [], "proxies": []}
                
                # Add new proxy
                proxy = {
                    "ip": ip,
                    "port": port,
                    "username": username,
                    "password": password,
                    "status": "Active"
                }
                
                if "proxies" not in config:
                    config["proxies"] = []
                
                config["proxies"].append(proxy)
                
                # Save config
                with open("monitor_config.json", 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.log_message(f"Added proxy: {ip}:{port}", "success")
                self.refresh_proxies()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add proxy: {e}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Save", command=save_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def edit_proxy(self):
        """Dialog to edit an existing proxy"""
        selection = self.proxy_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a proxy to edit")
            return
        
        # Get selected proxy
        item = self.proxy_tree.item(selection[0])
        values = item['values']
        
        # Extract current values
        current_ip_port = values[0]
        current_username = values[1]
        current_password = values[2]
        
        # Parse IP and port
        if ':' in current_ip_port:
            current_ip, current_port = current_ip_port.split(':', 1)
        else:
            current_ip = current_ip_port
            current_port = ""
        
        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Proxy")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Form
        ttk.Label(dialog, text="IP Address:").pack(pady=5)
        ip_var = tk.StringVar(value=current_ip)
        ip_entry = ttk.Entry(dialog, textvariable=ip_var, width=40)
        ip_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Port:").pack(pady=5)
        port_var = tk.StringVar(value=current_port)
        port_entry = ttk.Entry(dialog, textvariable=port_var, width=40)
        port_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Username:").pack(pady=5)
        username_var = tk.StringVar(value=current_username)
        username_entry = ttk.Entry(dialog, textvariable=username_var, width=40)
        username_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Password:").pack(pady=5)
        password_var = tk.StringVar(value=current_password)
        password_entry = ttk.Entry(dialog, textvariable=password_var, width=40, show="*")
        password_entry.pack(pady=5)
        
        def save_proxy():
            ip = ip_var.get().strip()
            port = port_var.get().strip()
            username = username_var.get().strip()
            password = password_var.get().strip()
            
            if not all([ip, port, username, password]):
                messagebox.showerror("Error", "Please fill in all fields")
                return
            
            try:
                # Load existing config
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                # Find and update the proxy
                for proxy in config.get("proxies", []):
                    if (proxy["ip"] == current_ip and 
                        proxy["port"] == current_port and 
                        proxy["username"] == current_username):
                        proxy["ip"] = ip
                        proxy["port"] = port
                        proxy["username"] = username
                        proxy["password"] = password
                        break
                
                # Save config
                with open("monitor_config.json", 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.log_message(f"Updated proxy: {ip}:{port}", "success")
                self.refresh_proxies()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update proxy: {e}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Save", command=save_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def remove_proxy(self):
        """Remove a proxy from the list"""
        selection = self.proxy_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a proxy to remove")
            return
        
        item = self.proxy_tree.item(selection[0])
        proxy_info = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove proxy '{proxy_info}'?"):
            try:
                # Load config
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                # Parse IP and port
                if ':' in proxy_info:
                    ip, port = proxy_info.split(':', 1)
                else:
                    ip = proxy_info
                    port = ""
                
                # Remove proxy
                config["proxies"] = [p for p in config.get("proxies", []) 
                                   if not (p["ip"] == ip and p["port"] == port)]
                
                # Save config
                with open("monitor_config.json", 'w') as f:
                    json.dump(config, f, indent=4)
                
                self.log_message(f"Removed proxy: {proxy_info}", "success")
                self.refresh_proxies()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove proxy: {e}")
    
    def import_proxies(self):
        """Import proxies from a text file"""
        filename = filedialog.askopenfilename(
            title="Select Proxy List File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            imported_count = 0
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Load existing config
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
            else:
                config = {"channels": [], "proxies": []}
            
            if "proxies" not in config:
                config["proxies"] = []
            
            for line in lines:
                line = line.strip()
                if line and ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 4:
                        ip, port, username, password = parts[:4]
                        
                        # Check if proxy already exists
                        exists = any(p["ip"] == ip and p["port"] == port 
                                   for p in config["proxies"])
                        
                        if not exists:
                            proxy = {
                                "ip": ip,
                                "port": port,
                                "username": username,
                                "password": password,
                                "status": "Active"
                            }
                            config["proxies"].append(proxy)
                            imported_count += 1
            
            # Save config
            with open("monitor_config.json", 'w') as f:
                json.dump(config, f, indent=4)
            
            self.log_message(f"Imported {imported_count} proxies from {filename}", "success")
            self.refresh_proxies()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import proxies: {e}")
    
    def refresh_proxies(self):
        """Refresh the proxy list display"""
        # Clear existing items
        for item in self.proxy_tree.get_children():
            self.proxy_tree.delete(item)
        
        try:
            if os.path.exists("monitor_config.json"):
                with open("monitor_config.json", 'r') as f:
                    config = json.load(f)
                
                for proxy in config.get("proxies", []):
                    ip_port = f"{proxy['ip']}:{proxy['port']}"
                    username = proxy.get('username', '')
                    password = proxy.get('password', '')
                    status = proxy.get('status', 'Active')
                    
                    self.proxy_tree.insert('', 'end', values=(ip_port, username, password, status))
                    
        except Exception as e:
            self.log_message(f"Error refreshing proxies: {e}", "error")
    
    def clear_proxy_environment(self):
        """Clear proxy environment variables"""
        try:
            # Remove proxy environment variables
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
            if 'http_proxy' in os.environ:
                del os.environ['http_proxy']
            if 'https_proxy' in os.environ:
                del os.environ['https_proxy']
            
            self.log_message("🧹 Cleared proxy environment variables", "info")
        except Exception as e:
            self.log_message(f"⚠️ Error clearing proxy environment: {e}", "warning")
    
    def clear_proxy_worker(self, worker_num):
        """Clear proxy environment variables for a specific worker"""
        try:
            # Remove proxy environment variables
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
            if 'http_proxy' in os.environ:
                del os.environ['http_proxy']
            if 'https_proxy' in os.environ:
                del os.environ['https_proxy']
            
            self.log_message(f"🧹 Worker {worker_num}: Cleared proxy environment variables", "info")
        except Exception as e:
            self.log_message(f"⚠️ Worker {worker_num}: Error clearing proxy environment: {e}", "warning")
    
    def create_proxy_session(self, proxy_config):
        """Create a requests session with proxy configuration"""
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Create session with proxy
            session = requests.Session()
            
            # Configure proxy
            if proxy_config:
                proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['ip']}:{proxy_config['port']}"
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                session.proxies.update(proxies)
                
                self.log_message(f"🌐 Created proxy session: {proxy_config['ip']}:{proxy_config['port']}", "info")
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            return session
            
        except ImportError:
            self.log_message("⚠️ Requests library not available, using default session", "warning")
            return None
        except Exception as e:
            self.log_message(f"⚠️ Error creating proxy session: {e}", "warning")
            return None
    
    def configure_youtube_monitor_proxy(self, yt_monitor, proxy_config):
        """Configure proxy on YouTubeMonitor instance"""
        try:
            if not proxy_config or not yt_monitor:
                return False
            
            # Method 1: Try to set proxy directly on the monitor
            if hasattr(yt_monitor, 'set_proxy'):
                try:
                    yt_monitor.set_proxy(
                        proxy_config['ip'],
                        proxy_config['port'],
                        proxy_config['username'],
                        proxy_config['password']
                    )
                    self.log_message(f"✅ Proxy configured on YouTubeMonitor: {proxy_config['ip']}:{proxy_config['port']}", "success")
                    return True
                except Exception as e:
                    self.log_message(f"⚠️ YouTubeMonitor.set_proxy failed: {e}", "warning")
            
            # Method 2: Try to set proxy on the browser instance
            if hasattr(yt_monitor, 'browser') and hasattr(yt_monitor.browser, 'set_proxy'):
                try:
                    yt_monitor.browser.set_proxy(
                        proxy_config['ip'],
                        proxy_config['port'],
                        proxy_config['username'],
                        proxy_config['password']
                    )
                    self.log_message(f"✅ Proxy configured on browser: {proxy_config['ip']}:{proxy_config['port']}", "success")
                    return True
                except Exception as e:
                    self.log_message(f"⚠️ Browser.set_proxy failed: {e}", "warning")
            
            # Method 3: Try to set proxy on the TikTok uploader
            if hasattr(yt_monitor, 'tiktok_uploader') and hasattr(yt_monitor.tiktok_uploader, 'set_proxy'):
                try:
                    yt_monitor.tiktok_uploader.set_proxy(
                        proxy_config['ip'],
                        proxy_config['port'],
                        proxy_config['username'],
                        proxy_config['password']
                    )
                    self.log_message(f"✅ Proxy configured on TikTok uploader: {proxy_config['ip']}:{proxy_config['port']}", "success")
                    return True
                except Exception as e:
                    self.log_message(f"⚠️ TikTok uploader.set_proxy failed: {e}", "warning")
            
            # Method 4: Set environment variables as fallback
            proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['ip']}:{proxy_config['port']}"
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            os.environ['http_proxy'] = proxy_url
            os.environ['https_proxy'] = proxy_url
            
            self.log_message(f"✅ Proxy configured via environment variables: {proxy_config['ip']}:{proxy_config['port']}", "success")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Failed to configure proxy on YouTubeMonitor: {e}", "error")
            return False

def main():
    root = tk.Tk()
    app = YouTubeMonitorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
