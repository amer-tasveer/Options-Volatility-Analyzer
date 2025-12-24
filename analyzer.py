import tkinter as tk
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotx
import threading
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ib_api import IBapi
import TKinterModernThemes as TKMT

class Analyzer(TKMT.ThemedTKinterFrame):
    def __init__(self, theme, mode, usecommandlineargs=True, usethemeconfigfile=True):
        super().__init__("Analyzer", theme, mode, usecommandlineargs, usethemeconfigfile)
        plt.style.use(matplotx.styles.dracula)


        self.root.title("Options Volatility Analyzer")
        self.root.geometry("1500x1300")
        self.root.resizable(False, False)

        #Data

        self.option_data=None
        self.volility_data=None
        self.current_implied_vol=None

        self.ib_app=IBapi()
        self.connected=False
        self.vol_annularization_factor=252  #Trading days in a year
        self.strategies = ["Long Straddle", "Short Straddle", "Long Strangle", "Short Strangle", "Iron Butterfly"]
        self.setup_ui()



    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame.columnconfigure(0, weight=1) # Left
        main_frame.columnconfigure(1, weight=1) # Middle
        main_frame.columnconfigure(2, weight=2) # Right

        # Title Label
        title_label = ttk.Label(main_frame, text="Options Volatility Analyzer", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0,20))

        # Left Column
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        self.setup_connection_section(left_frame, 0)
        self.setup_query_data_section(left_frame, 1)
        self.setup_iv_market_data_section(left_frame, 2)

        # Middle Column
        middle_frame = ttk.LabelFrame(main_frame, text="Strategy Setup", padding="10")
        middle_frame.grid(row=1, column=1, sticky="nsew", padx=10)
        
        ttk.Label(middle_frame, text="Select Strategy:").pack(pady=(5, 0), anchor="w")
        self.strategy_var = tk.StringVar()
        self.strategy_dropdown = ttk.Combobox(middle_frame, textvariable=self.strategy_var, values=self.strategies, state="readonly")
        self.strategy_dropdown.pack(fill="x", pady=5)
        self.strategy_dropdown.bind("<<ComboboxSelected>>", self.update_payoff_plot)

        ttk.Label(middle_frame, text="Underlying Price:").pack(anchor="w")
        self.price_entry = ttk.Entry(middle_frame)
        self.price_entry.insert(0, "100")
        self.price_entry.pack(fill="x", pady=5)

        update_btn = ttk.Button(middle_frame, text="Update Plot", command=self.update_payoff_plot)
        update_btn.pack(pady=20)
        
        # Right Column  
        self.right_frame = ttk.LabelFrame(main_frame, text="Strategy Payoff", padding="5")
        self.right_frame.grid(row=1, column=2, sticky="nsew", padx=10)

        # Initialize Plot
        self.fig_payoff, self.ax_payoff = plt.subplots(figsize=(5, 4))
        self.canvas_payoff = FigureCanvasTkAgg(self.fig_payoff, self.right_frame)
        self.canvas_payoff.get_tk_widget().pack(fill="both", expand=True)

        self.setup_status_section(main_frame,4)
        self.setup_plot(main_frame,5)

    def setup_connection_section(self, parent, row):
        conn_frame = ttk.LabelFrame(parent, text="Interactive Brokers Connection", padding="10")
        conn_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        conn_frame.columnconfigure(3, weight=1)
        
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(conn_frame, textvariable=self.host_var, width=15).grid(row=0, column=1, padx=(0, 15), sticky=(tk.W, tk.E))
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=(0, 5), sticky=tk.W)
        self.port_var = tk.StringVar(value="7497")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=10).grid(row=0, column=3, padx=(0, 15), sticky=(tk.W, tk.E))
        
        button_frame = ttk.Frame(conn_frame)
        button_frame.grid(row=1, column=0, columnspan=4, pady=(10, 0))
        
        self.connect_btn = ttk.Button(button_frame, text="Connect to IB", command=self.connect_ib)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_ib, state="disabled")
        self.disconnect_btn.pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(conn_frame, text="● Disconnected", foreground="red")
        self.status_label.grid(row=2, column=0, columnspan=4, pady=(5, 0))

    def market_data_connection(self,parent, row):
        data_frame = ttk.LabelFrame(parent, text="📊 Market Data & Parameters", padding="10")
        data_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        data_frame.columnconfigure(1, weight=1)
        
        ttk.Label(data_frame, text="Ticker:").grid(row=0, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        ticker_frame = ttk.Frame(data_frame)
        ticker_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        ticker_frame.columnconfigure(0, weight=1)
        
        self.ticker_var = tk.StringVar(value="AAPL")
        ttk.Entry(ticker_frame, textvariable=self.ticker_var, width=12, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.fetch_btn = ttk.Button(ticker_frame, text="Fetch Data", command=self.fetch_market_data, state="disabled")
        self.fetch_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Label(data_frame, text="Spot Price:").grid(row=1, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.spot_price_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.spot_price_var, width=15, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        
        ttk.Label(data_frame, text="Strike Price:").grid(row=2, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.strike_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.strike_var, width=15, font=("Arial", 10, "bold")).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        
        ttk.Label(data_frame, text="IV (%):").grid(row=3, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.iv_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.iv_var, width=15, font=("Arial", 10, "bold")).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        
        ttk.Label(data_frame, text="Days to Expiry:").grid(row=4, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.days_var = tk.StringVar(value="30")
        ttk.Entry(data_frame, textvariable=self.days_var, width=15, font=("Arial", 10, "bold")).grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        

    def setup_query_data_section(self,parent,row):
        data_frame = ttk.LabelFrame(parent, text="Data Query", padding="5")
        data_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(data_frame, text="Symbol:").grid(row=0, column=0, padx=(0, 5))
        self.symbol_var = tk.StringVar(value="SPY")
        ttk.Entry(data_frame, textvariable=self.symbol_var, width=10).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(data_frame, text="Duration:").grid(row=0, column=2, padx=(0, 5))
        self.duration_var = tk.StringVar(value="2 Y")
        ttk.Entry(data_frame, textvariable=self.duration_var, width=10).grid(row=0, column=3, padx=(0, 10))

    def setup_status_section(self, parent, row):
        """Creates a scrollable status/log box at the bottom"""
        status_frame = ttk.LabelFrame(parent, text="System Status & Logs", padding="5")
        status_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        
        self.status_log = scrolledtext.ScrolledText(
            status_frame, 
            height=6, 
            font=("Consolas", 9), 
            state='disabled', 
            bg="#1e1e1e", 
            fg="#d4d4d4"
        )
        self.status_log.pack(fill="x", expand=True)
        self.log_message("System initialized. Ready to connect to IB...")

    def log_message(self, message):
        """Helper to add messages to the scrollable status box"""
        self.status_log.configure(state='normal')
        self.status_log.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.status_log.see(tk.END) # Auto-scroll to bottom
        self.status_log.configure(state='disabled')

    def setup_iv_market_data_section(self,parent, row):
        vol_frame = ttk.LabelFrame(parent, text="Current Implied Volatility", padding="5")
        vol_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(vol_frame, text="Current IV:").grid(row=0, column=0, padx=(0, 5))
        self.current_vol_label = ttk.Label(vol_frame, text="N/A", font=("Arial", 12, "bold"))
        self.current_vol_label.grid(row=0, column=1, padx=(0, 20))
        
        ttk.Label(vol_frame, text="Computation:").grid(row=0, column=2, padx=(0, 5))
        self.vol_computation_label = ttk.Label(vol_frame, text="No data", font=("Arial", 10))
        self.vol_computation_label.grid(row=0, column=3, padx=(0, 10))
        

        
        ttk.Label(vol_frame, text="Vol Range:").grid(row=0, column=4, padx=(0, 5))
        self.vol_range_label = ttk.Label(vol_frame, text="N/A", font=("Arial", 10))
        self.vol_range_label.grid(row=0, column=5)

    def setup_plot(self,parent,row):
        plot_frame = ttk.LabelFrame(parent, text="Implied Volatility Analysis Results", padding="5")
        plot_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        
        self.fig_main, (self.ax1, self.ax2, self.ax3) = plt.subplots(1, 3, figsize=(10, 6))
        self.canvas_main = FigureCanvasTkAgg(self.fig_main, plot_frame)
        self.canvas_main.get_tk_widget().pack(fill="both", expand=True)


    def connect_ib(self):
        try:
            host = self.host_var.get()
            port = int(self.port_var.get())
            
            self.log_message(f"Connecting to IB at {host}:{port}...")
            
            # Start connection in separate thread
            def connect_thread():
                try:
                    self.ib_app.connect(host, port, 0)
                    self.ib_app.run()
                except Exception as e:
                    self.log_message(f"Connection error: {e}")
                    
            thread = threading.Thread(target=connect_thread, daemon=True)
            thread.start()
            
            # Wait for connection
            for _ in range(50):  # Wait up to 5 seconds
                if self.ib_app.connected:
                    break
                time.sleep(0.1)
                
            if self.ib_app.connected:
                self.connected = True
                self.connect_btn.config(state="disabled")
                self.disconnect_btn.config(state="normal")
                self.query_btn.config(state="normal")
                self.log_message("Successfully connected to Interactive Brokers")
            else:
                self.log_message("Failed to connect to Interactive Brokers")
                
        except Exception as e:
            self.log_message(f"Connection error: {e}")

    def disconnect_ib(self):
        try:
            self.ib_app.disconnect()
            self.connected = False
            self.connect_btn.config(state="normal")
            self.disconnect_btn.config(state="disabled")
            
            # Reset volatility display
            self.current_implied_vol = None
            self.update_current_vol_display()
            
            self.log_message("Disconnected from Interactive Brokers")
        except Exception as e:
            self.log_message(f"Disconnect error: {e}")


    def fetch_market_data(self):
        pass

    def update_payoff_plot(self, event=None):
            strategy = self.strategy_var.get()
            try:
                spot = float(self.price_entry.get())
            except ValueError:
                spot = 100

            self.ax_payoff.clear()
            
            x = np.linspace(spot * 0.8, spot * 1.2, 100)
            y = np.zeros_like(x)
            k = spot 
            premium = 5 
            
            if strategy == "Long Straddle":
                y = np.maximum(0, x - k) + np.maximum(0, k - x) - (premium * 2)
            elif strategy == "Short Straddle":
                y = (premium * 2) - (np.maximum(0, x - k) + np.maximum(0, k - x))
            elif strategy == "Long Strangle":
                k_put, k_call = k - 5, k + 5
                y = np.maximum(0, k_put - x) + np.maximum(0, x - k_call) - premium
            elif strategy == "Short Strangle":
                k_put, k_call = k - 5, k + 5
                y = premium - (np.maximum(0, k_put - x) + np.maximum(0, x - k_call))
            elif strategy == "Iron Butterfly":
                y = np.maximum(0, x - (k-5)) - 2*np.maximum(0, x-k) + np.maximum(0, x-(k+5))

            self.ax_payoff.plot(x, y, color='#0078d4', lw=2)
            self.ax_payoff.axhline(0, color='black', lw=1)
            self.ax_payoff.axvline(spot, color='gray', linestyle='--')
            self.ax_payoff.set_title(f"{strategy} Payoff")
            self.ax_payoff.fill_between(x, y, 0, where=(y > 0), color='green', alpha=0.3)
            self.ax_payoff.fill_between(x, y, 0, where=(y < 0), color='red', alpha=0.3)
            
            self.canvas_payoff.draw()
            self.log_message(f"Updated payoff plot for {strategy}")


if __name__ == "__main__":
    app = Analyzer("sun-valley", "dark")
    app.root.mainloop() 