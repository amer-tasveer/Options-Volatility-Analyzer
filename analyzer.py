import tkinter as tk
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotx
import threading
import time
import pandas as pd
import numpy as np        
from scipy import stats
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
        # self.root.resizable(False, False)

        #Data

        self.option_data = None
        self.volility_data = None
        self.current_implied_vol = None

        self.ib_app = IBapi()
        self.connected = False
        self.vol_annularization_factor = 252  #Trading days in a year
        self.strategies = ["Long Straddle", "Short Straddle", "Long Strangle", "Short Strangle", "Iron Butterfly"]
        self.setup_ui()



    def setup_ui(self):
        self.main_canvas = tk.Canvas(self.root, highlightthickness=0)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.main_canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_content = ttk.Frame(self.main_canvas, padding="15")
        
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")

        self.scrollable_content.bind("<Configure>", self._on_frame_configure)
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)
        
        self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.scrollable_content.columnconfigure(0, weight=1) # Left
        self.scrollable_content.columnconfigure(1, weight=1) # Middle
        self.scrollable_content.columnconfigure(2, weight=2) # Right

        title_label = ttk.Label(self.scrollable_content, text="Options Volatility Analyzer", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0,20))

        left_frame = ttk.Frame(self.scrollable_content)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=10)
        self.setup_connection_section(left_frame, 0)
        self.setup_query_data_section(left_frame, 1)
        self.setup_iv_market_data_section(left_frame, 2)

        # Middle Column
        middle_frame = ttk.LabelFrame(self.scrollable_content, text="Strategy Setup", padding="10")
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
        self.right_frame = ttk.LabelFrame(self.scrollable_content, text="Strategy Payoff", padding="5")
        self.right_frame.grid(row=1, column=2, sticky="nsew", padx=10)

        # Initialize Plot
        self.fig_payoff, self.ax_payoff = plt.subplots(figsize=(5, 4))
        self.canvas_payoff = FigureCanvasTkAgg(self.fig_payoff, self.right_frame)
        self.canvas_payoff.get_tk_widget().pack(fill="both", expand=True)

        self.setup_status_section(self.scrollable_content,4)
        self.setup_plot(self.scrollable_content,5)
        self.setup_iv_rv_market_data_plot_section(self.scrollable_content,6)

    def _on_frame_configure(self, event):
            # Update scrollregion to match the size of the inner frame
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Resize the inner frame to match the canvas width
        self.main_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def setup_connection_section(self, parent, row):
        conn_frame = ttk.LabelFrame(parent, text="Interactive Brokers Connection", padding="10")
        conn_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        conn_frame.columnconfigure(3, weight=1)
        
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(conn_frame, textvariable=self.host_var, width=15).grid(row=0, column=1, padx=(0, 15), sticky=(tk.W, tk.E))
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=(0, 5), sticky=tk.W)
        self.port_var = tk.StringVar(value="7496")
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
        self.query_btn = ttk.Button(data_frame, text="Query", command=self.fetch_market_data, state="disabled")
        self.query_btn.grid(row=0, column=4, padx=(10, 0))

    def setup_status_section(self, parent, row):
        """Creates a scrollable status/log box at the bottom"""
        status_frame = ttk.LabelFrame(parent, text="System Status & Logs", padding="5")
        status_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=(0, 10))
        
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

                
        self.analyse_btn = ttk.Button(vol_frame, text="Analyse IV", command=self.analyse_implied_vol)
        self.analyse_btn.grid(row=0, column=4, padx=(10, 0))
        
        # ttk.Label(vol_frame, text="Computation:").grid(row=0, column=2, padx=(0, 5))
        # self.vol_computation_label = ttk.Label(vol_frame, text="No data", font=("Arial", 10))
        # self.vol_computation_label.grid(row=0, column=3, padx=(0, 10))
        

        
        # ttk.Label(vol_frame, text="Vol Range:").grid(row=0, column=4, padx=(0, 5))
        # self.vol_range_label = ttk.Label(vol_frame, text="N/A", font=("Arial", 10))
        # self.vol_range_label.grid(row=0, column=5)

    def setup_iv_rv_market_data_plot_section(self,parent,row):
        vol_frame = ttk.LabelFrame(parent, text="IV vs RV Market Data", padding="5")
        vol_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.fig_ivrv, (self.ax_iv_rv, self.ax_kurt, self.ax_vix) = plt.subplots(1, 3, figsize=(5, 4))
        self.canvas_ivrv = FigureCanvasTkAgg(self.fig_ivrv, vol_frame)
        self.canvas_ivrv.get_tk_widget().pack(fill="both", expand=True)


    def setup_plot(self,parent,row):
        plot_frame = ttk.LabelFrame(parent, text="Implied Volatility Analysis Results", padding="5")
        plot_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)
        
        self.fig_main, (self.ax_iv1, self.ax_iv2, self.ax_iv3) = plt.subplots(1, 3, figsize=(5, 4))
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
                self.status_label.config(text="● Connected", foreground="green")
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
        ticker = self.symbol_var.get().strip().upper()
        duration = self.duration_var.get().strip()

        self.log_message(f"Querying Implied Volatility for {ticker}...")
        self.ib_app.historical_data.clear()   

        contract=self.ib_app.create_contract(ticker)
        vix_contract=self.ib_app.create_vix_contract()


        self.ib_app.reqHistoricalData(
            reqId=1,
            contract=contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="1 day",
            whatToShow="OPTION_IMPLIED_VOLATILITY",
            useRTH=1, 
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        timeout = 15
        start_time=time.time()
        while 1 not in self.ib_app.historical_data and (time.time()-start_time)<timeout:
            time.sleep(0.1)
        
        if 1 in self.ib_app.historical_data:
            data=self.ib_app.historical_data[1]
            if len(data)>0:
                self.equity_iv = pd.DataFrame(data)          
                self.equity_iv['date'] = pd.to_datetime(self.equity_iv['date'], format='%Y%m%d')

                self.equity_iv.set_index("date", inplace=True)
                self.equity_iv['iv'] = self.equity_iv['close']

                self.log_message(f"Received {len(self.equity_iv)} implied vol points for {ticker}")
                self.log_message(f"Date range: {self.equity_iv.index.min()} to {self.equity_iv.index.max()}")
                self.log_message("Note: All iVol Values are Annualized")

        self.ib_app.reqHistoricalData(
            reqId=2,
            contract=contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=1, 
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        timeout = 15
        start_time=time.time()
        while 2 not in self.ib_app.historical_data and (time.time()-start_time)<timeout:
            time.sleep(0.1)
        
        if 2 in self.ib_app.historical_data:
            data = self.ib_app.historical_data[2]

            if len(data) > 0:
                self.stock_data = pd.DataFrame(data)
                self.stock_data['date'] = pd.to_datetime(self.stock_data['date'], format='%Y%m%d')
                self.stock_data.set_index("date", inplace=True)

                self.log_message(f"Received {len(self.stock_data)} stock points for {ticker}")

        self.ib_app.reqHistoricalData(
            reqId=3,
            contract=vix_contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=1, 
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )

        timeout = 15
        start_time=time.time()
        while 3 not in self.ib_app.historical_data and (time.time()-start_time)<timeout:
            time.sleep(0.1)

        if 3 in self.ib_app.historical_data:
            data = self.ib_app.historical_data[3]

            if len(data)>0:
                self.vix_data = pd.DataFrame(data)
                self.vix_data['date'] = pd.to_datetime(self.vix_data['date'], format='%Y%m%d')
                self.vix_data.set_index("date", inplace=True)
                self.log_message(f"Received {len(self.vix_data)} vix points for {ticker}")

        self.process_implied_vol_data()
        self.process_iv_rv_kurt_data()

    def clear_all_data(self):
        self.ib_app.historical_data.clear()
        for k in self.ib_app.historical_data.keys():
            self.ib_app.historical_data[k] = []

    def process_iv_rv_kurt_data(self):
        yz_series = self.calculate_yang_zhang(self.stock_data)
        log_returns = np.log(self.stock_data['close'] / self.stock_data['close'].shift(1))

        if yz_series is not None:
            latest_yz = yz_series.iloc[-1]
            self.stock_data['yz_vol'] = yz_series # Store it for plotting

            self.stock_data['vrp']=self.equity_iv['iv']-self.stock_data['yz_vol']
            self.log_message(f"YZ Historical Vol (30d): {latest_yz*100:.2f}%")

        self.stock_data['kurtosis'] = log_returns.rolling(window=30).kurt()

    def process_implied_vol_data(self):
        if self.equity_iv is None or self.equity_iv.empty:
            self.log_message("No equity data to process.")
            return
        
        self.log_message("Processing implied volatility data...")
        
        iv_series=self.equity_iv['iv']

        self.equity_iv['iv_percentile'] = iv_series.rolling(window=252, min_periods=1).apply(
            lambda x: stats.percentileofscore(x, x.iloc[-1]) / 100
        )

        if iv_series.empty:
            self.log_message("No valid implied volatility data found.")
            return
        
        self.current_implied_vol = iv_series.iloc[-1]

        self.volatility_data = self.equity_iv[['iv', 'iv_percentile']].copy()


        self.log_message(f"Current iVol: {self.current_implied_vol:.4f} ({self.current_implied_vol*100:.2f}%)")
        self.log_message(f"IV Range: {self.equity_iv['iv'].min():.4f} - {self.equity_iv['iv'].max():.4f}")
        
        self.update_current_vol_display()

    def calculate_yang_zhang(self, df, window=30):
        """Calculates Yang-Zhang Volatility for a dataframe with OHLC columns."""
        try:
            log_ho = np.log(df['high'] / df['open'])
            log_lo = np.log(df['low'] / df['open'])
            log_co = np.log(df['close'] / df['open'])
            
            log_oc = np.log(df['open'] / df['close'].shift(1))
            log_cc = np.log(df['close'] / df['close'].shift(1))
            
            rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
            
            k = 0.34 / (1.34 + (window + 1) / (window - 1))
            
            sigma_open_sq = (log_oc**2).rolling(window).var() 
            sigma_close_sq = (log_cc**2).rolling(window).var() 
            sigma_rs_sq = rs.rolling(window).mean()
            
            yz_sq = sigma_open_sq + k * sigma_close_sq + (1 - k) * sigma_rs_sq
            
            # Annualize and return
            return np.sqrt(yz_sq) * np.sqrt(self.vol_annularization_factor)
        except Exception as e:
            self.log_message(f"YZ Calculation Error: {e}")
            return None

    def analyse_implied_vol(self):
        if self.equity_iv is None or self.volatility_data is None:
            messagebox.showerror("Error", "No iVOL Data is Available for Analysis")
            return
        
        self.log_message("Analyzing iVOL Data")
        vol_forward_30d = self.volatility_data['iv'].rolling(window=30, min_periods=1).mean().shift(-30)

        analysis_df = pd.DataFrame({
            'current_vol':self.volatility_data['iv'],
            'forward_30d_vol':vol_forward_30d,
            'vol_diff':vol_forward_30d-self.volatility_data['iv'],
            'vol_percentile':self.volatility_data['iv_percentile']
        })

        analysis_df = analysis_df.dropna()
        if len(analysis_df) < 30:
            self.log_message("Insufficient iVOL Data for Analysis")
            return
        
        slope1, intercept1, r_value1, p_value1, std_error1 = stats.linregress(
            analysis_df['current_vol'], analysis_df['forward_30d_vol']
        )

        slope2, intercept2, r_value2, p_value2, std_error2 = stats.linregress(
            analysis_df['current_vol'], analysis_df['vol_diff']
        )

        if slope1!=1:
            intersection_x = intercept1/(1-slope1)
        else:
            intersection_x = analysis_df['current_vol'].median()


        high_vol_regime = analysis_df['current_vol'] > intersection_x
        low_vol_regime = analysis_df['current_vol'] <= intersection_x

        if high_vol_regime.sum() > 10:
            slope_high, intercept_high, r_high, p_high, std_error_high = stats.linregress(
                analysis_df.loc[high_vol_regime, 'current_vol'], analysis_df.loc[high_vol_regime, 'vol_diff']
            )
        else:
            slope_high = intercept_high = r_high = p_high = std_error_high = None

        if low_vol_regime.sum() > 10:
            slope_low, intercept_low, r_low, p_low, std_error_low = stats.linregress(
                analysis_df.loc[low_vol_regime, 'current_vol'], analysis_df.loc[low_vol_regime, 'vol_diff']
            )
        else:
            slope_low = intercept_low = r_low = p_low = std_error_low = None

        self.ax_iv1.clear()
        self.ax_iv2.clear()
        self.ax_iv3.clear()

        self.ax_iv1.scatter(analysis_df['current_vol'], analysis_df['forward_30d_vol'], alpha=.6, s=20)

        x_range = np.linspace(analysis_df['current_vol'].min(), analysis_df['current_vol'].max(), 100)
        y_pred1 = slope1 * x_range + intercept1

        self.ax_iv1.plot(x_range, y_pred1, 'r-', linewidth=2, label=f"Regression R^2 = {r_value1**2:.3f}")

        min_val = min(analysis_df['current_vol'].min(), analysis_df['forward_30d_vol'].min())
        max_val = max(analysis_df['current_vol'].max(), analysis_df['forward_30d_vol'].max())
        self.ax_iv1.plot([min_val, max_val], [min_val, max_val], 'k--', linewidth=1, alpha=.7, label='y=x (No Change)')

        self.ax_iv1.set_xlabel("Current Implied Volatility")
        self.ax_iv1.set_ylabel("30-Day Forward Average iVOL")
        self.ax_iv1.set_title(f"Forward iVOL vs Current iVOL \n y = {slope1:.3f}x + {intercept1:.3f}, R^2 = {r_value1**2:.3f}")
        self.ax_iv1.legend()
        self.ax_iv1.grid(True, alpha=.3)

        self.ax_iv2.scatter(analysis_df.loc[high_vol_regime, 'current_vol'], 
                         analysis_df.loc[high_vol_regime, 'vol_diff'],
                         alpha=.6, s=20, color='red', label='High Vol Regime')
        self.ax_iv2.scatter(analysis_df.loc[low_vol_regime, 'current_vol'], 
                         analysis_df.loc[low_vol_regime, 'vol_diff'],
                         alpha=.6, s=20, color='blue', label='Low Vol Regime')
        
        if slope_high is not None:
            x_high = analysis_df.loc[high_vol_regime, 'current_vol']
            if len(x_high) > 0:
                x_range_high = np.linspace(x_high.min(), x_high.max(), 100)
                y_pred_high = slope_high * x_range_high + intercept_high
                self.ax_iv2.plot(x_range_high, y_pred_high, 'r-', linewidth=2,
                              label=f"High Vol R^2 = {r_high**2:.3f}")
                
        if slope_low is not None:
            x_low = analysis_df.loc[low_vol_regime, 'current_vol']
            if len(x_low) > 0:
                x_range_low = np.linspace(x_low.min(), x_low.max(), 100)
                y_pred_low = slope_low * x_range_low + intercept_low
                self.ax_iv2.plot(x_range_low, y_pred_low, 'r-', linewidth=2,
                              label=f"Low Vol R^2 = {r_low**2:.3f}")
                
        self.ax_iv2.axhline(y = 0, color='k', linestyle='--', linewidth=1, alpha=.7, label='No Change (y=0)')
        self.ax_iv2.axvline(x = intersection_x, color='g', linestyle=':', linewidth=1, alpha=.7,
                         label=f"Regime Split (Vol={intersection_x:.3f})")
        
        self.ax_iv2.set_xlabel("Current Implied Volatility")
        self.ax_iv2.set_ylabel("Vol Difference (Forward - Current)")
        self.ax_iv2.set_title("Vol Difference vs Current Vol (Regime Analysis)")
        self.ax_iv2.legend()
        self.ax_iv2.grid(True, alpha=.3)

        self.ax_iv3.plot(self.volatility_data.index, self.volatility_data['iv'],
                      label="Implied Volatility", linewidth=1)
        
        vol_75th = self.volatility_data['iv'].quantile(.75)
        vol_25th = self.volatility_data['iv'].quantile(.25)

        self.ax_iv3.axhline(y=vol_75th, color='red', linestyle='--', alpha=.7, label='75th Percentile')
        self.ax_iv3.axhline(y=vol_25th, color='green', linestyle='--', alpha=.7, label='25th Percentile')
        self.ax_iv3.axhline(y=self.volatility_data['iv'].mean(), color='black', linestyle='--', alpha=.7, label='Mean')
    
        if self.current_implied_vol is not None:
            self.ax_iv3.scatter(self.volatility_data.index[-1], self.current_implied_vol,
                             color='red', s=120, zorder=5, label='Current iVOL')
        
        self.ax_iv3.set_xlabel('Date')
        self.ax_iv3.set_ylabel('Implied Volatility')
        self.ax_iv3.set_title("Implied Volatility Time Series with Regime Bands")
        self.ax_iv3.legend()
        self.ax_iv3.grid(True, alpha=.3)
        self.ax_iv3.tick_params(axis='x', rotation=45)

        # Better date formatting and reduce clutter
        import matplotlib.dates as mdates

        self.ax_iv3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        self.ax_iv3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.ax_iv3.xaxis.set_minor_locator(mdates.MonthLocator())
        self.ax_iv3.tick_params(axis='x', rotation=45)

        self.fig_main.tight_layout()
        self.fig_main.subplots_adjust(bottom=0.18)
        self.canvas_main.draw()
        self.analyse_rv_iv_kurt()

    def analyse_rv_iv_kurt(self):

        import matplotlib.dates as mdates

        plt.ion()

        self.ax_iv_rv.clear()
        self.ax_kurt.clear()
        self.ax_vix.clear()


        combined = pd.concat([
            self.equity_iv['iv'], 
            self.stock_data['yz_vol']
        ], axis=1).dropna()
        combined.columns = ['IV', 'RV']
        combined['VRP'] = combined['IV'] - combined['RV']

        colors = ['green' if v >= 0 else 'red' for v in combined['VRP']]

        # Bar chart for VRP
        bars = self.ax_iv_rv.bar(
            combined.index, 
            combined['VRP'], 
            width=0.8, 
            color=colors, 
            alpha=0.8, 
            label='VRP (IV - RV)'
        )


        self.ax_iv_rv.axhline(0, color='white', linestyle='--', linewidth=1, alpha=0.7)

        self.ax_iv_rv.axhline(0.03, color='green', linestyle=':', alpha=0.7, label='+3% Rich')
        self.ax_iv_rv.axhline(0.05, color='darkgreen', linestyle='--', alpha=0.7, label='+5% Very Rich')

        current_vrp = combined['VRP'].iloc[-1] * 100
        self.ax_iv_rv.set_title(f"Volatility Risk Premium (Current: {current_vrp:+.2f}%)")
        self.ax_iv_rv.set_ylabel("VRP (Annualized Decimal)")
        self.ax_iv_rv.legend()
        self.ax_iv_rv.grid(True, alpha=0.3)

        self.ax_iv_rv.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        self.ax_iv_rv.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.ax_iv_rv.tick_params(axis='x', rotation=45)

        vrp_percentile = stats.percentileofscore(combined['VRP'] * 100, current_vrp)
        self.log_message(f"Current VRP: {current_vrp:+.2f}% (Percentile: {vrp_percentile:.0f}%)")
        kurt_series = self.stock_data['kurtosis'].dropna()
        
        if not kurt_series.empty:
            self.ax_kurt.plot(kurt_series.index, kurt_series, color='#ff9900', label='30D Excess Kurtosis')
            
            self.ax_kurt.axhline(y=0, color='white', linestyle='--', alpha=0.5, label='Normal Dist')
            self.ax_kurt.axhline(y=3, color='red', linestyle=':', alpha=0.7, label='High Risk (Fat Tails)')
            
            current_kurt = kurt_series.iloc[-1]
            self.ax_kurt.scatter(kurt_series.index[-1], current_kurt, color='red', s=100, zorder=5)
            
            self.ax_kurt.set_title(f"Kurtosis: {current_kurt:.2f} (Tail Risk)")
            self.ax_kurt.set_ylabel("Excess Kurtosis")
            self.ax_kurt.legend(loc='upper left', fontsize='small')
            self.ax_kurt.grid(True, alpha=.3)
            
            self.ax_kurt.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            self.ax_kurt.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            self.ax_kurt.tick_params(axis='x', rotation=45)

        self.ax_vix.set_xlabel("VIX")
        self.ax_vix.set_ylabel("Date")
        self.ax_vix.set_title("VIX")
        self.ax_vix.legend()
        self.ax_vix.grid(True, alpha=.3)

        self.ax_vix.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        self.ax_vix.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.ax_vix.tick_params(axis='x', rotation=45)

        self.ax_vix.plot(self.equity_iv.index, self.vix_data["close"],  color='black', linewidth=2, label=f"VIX")

        self.fig_ivrv.tight_layout()
        self.fig_ivrv.subplots_adjust(bottom=0.18)
        self.canvas_ivrv.draw()

    def update_current_vol_display(self):
        if self.current_implied_vol is None:
            self.current_vol_label.config(text="N/A", foreground='black')
            # self.vol_computation_label.config(text='No Data')
            # self.vol_range_label.config(text="N/A")
            # self.regime_label.config(text="N/A")
            # self.percentile_label.config(text="N/A")
            # self.reversion_label.config(text="N/A")

        else:
            self.current_vol_label.config(text=f'{self.current_implied_vol*100:.2f}%')
            # self.vol_computation_label.config(text=f'{self.current_implied_vol*100:.2f}%')

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