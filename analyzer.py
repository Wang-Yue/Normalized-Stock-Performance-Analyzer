import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk # MODIFIED IMPORT: Added NavigationToolbar2Tk

# --- 1. Financial Calculation Function (Same as final version) ---

def calculate_normalized_return(symbols, start_date_str, end_date_str):
    """
    Calculates the total return series for multiple symbols using the adjusted price,
    and normalizes the final result so the end value is $1.00.
    """
    
    # yfinance requires dates in YYYY-MM-DD format
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    
    # Fetch Data with Auto-Adjustment (assumes dividends/splits are included)
    try:
        data = yf.download(
            symbols, 
            start=start_date, 
            end=end_date, 
            auto_adjust=True, 
            progress=False
        )
    except Exception as e:
        raise ValueError(f"Error fetching data from Yahoo Finance: {e}")

    if data.empty:
        raise ValueError("No data found for the symbols in the given period. Check dates or symbols.")

    # Safely Select the Adjusted Price Data
    if len(symbols) == 1:
        # If only one symbol is downloaded, 'Close' is typically the adjusted column
        if 'Close' in data.columns:
             df_price = data['Close'].to_frame() # Convert Series to DataFrame for consistent logic
        else:
            raise ValueError("Data fetching error: 'Close' column not found.")
    else:
        # For multiple symbols (MultiIndex), try 'Adj Close' then 'Close'
        if 'Adj Close' in data.columns.get_level_values(0):
            df_price = data['Adj Close']
        elif 'Close' in data.columns.get_level_values(0):
            df_price = data['Close']
        else:
            raise ValueError("Data fetching error: Cannot find Adjusted or Close price columns.")
            
    # Remove rows with any NaN values to ensure proper division later
    df_price.dropna()

    if df_price.empty:
        raise ValueError("No overlapping data found for all symbols after cleaning.")
            
    # --- Normalize the Entire Series (End Value is $1) ---

    # Get the LAST (final) price for each stock.
    final_prices = df_price.iloc[-1]
    
    # Divide the entire DataFrame by the final price for each column (vectorized operation).
    df_normalized_worth = df_price.div(final_prices, axis=1)

    return df_normalized_worth

# --- 2. Tkinter Application Class ---

class StockAnalyzerApp:
    def __init__(self, root):
        self.root = root
        root.title("Normalized Stock Performance Analyzer")
        
        # --- Default Values ---
        self.end_date_default = datetime.now()
        self.start_date_default = self.end_date_default - timedelta(days=5*365) # Approx 5 years ago

        self.setup_ui()
        self.run_analysis() # Run analysis with defaults on startup

    def setup_ui(self):
        # Configure container frame
        main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # --- Input Widgets ---
        input_frame = ttk.LabelFrame(main_frame, text="Analysis Parameters", padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        input_frame.columnconfigure(1, weight=1)

        # Symbols Input
        ttk.Label(input_frame, text="Symbols (e.g., AAPL, VOO):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.symbols_var = tk.StringVar(value="AAPL, MSFT, GOOG, VOO")
        self.symbols_entry = ttk.Entry(input_frame, textvariable=self.symbols_var)
        self.symbols_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Start Date Input
        ttk.Label(input_frame, text="Start Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_date_var = tk.StringVar(value=self.start_date_default.strftime('%Y-%m-%d'))
        self.start_date_entry = ttk.Entry(input_frame, textvariable=self.start_date_var)
        self.start_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        # End Date Input
        ttk.Label(input_frame, text="End Date (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.end_date_var = tk.StringVar(value=self.end_date_default.strftime('%Y-%m-%d'))
        self.end_date_entry = ttk.Entry(input_frame, textvariable=self.end_date_var)
        self.end_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        # Run Button
        self.run_button = ttk.Button(input_frame, text="Run Analysis & Plot", command=self.run_analysis)
        self.run_button.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))

        # --- Plotting Area (Matplotlib) ---
        plot_frame = ttk.Frame(main_frame)
        main_frame.rowconfigure(1, weight=1)
        plot_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        # Create a figure for the plot
        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        
        # Embed the Matplotlib figure into Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        # FIXED: Use grid for the canvas to work with the layout
        self.canvas_widget.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)) 
        
        # --- Add Matplotlib Toolbar ---
        # Initialize the toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame, pack_toolbar=False)
        self.toolbar.update()
        # FIXED: Use grid for the toolbar and place it below the canvas (row=1)
        self.toolbar.grid(row=1, column=0, sticky=tk.W+tk.E) 
        # -----------------------------
        
        # Initial plot setup
        self.ax.set_title("Normalized Performance (Initial Run)")
        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Normalized Asset Worth (End Value = $1.00)")
        self.fig.tight_layout()

    def run_analysis(self):
        """Fetches data, calculates normalization, and updates the plot."""
        self.run_button.config(state=tk.DISABLED, text="Loading...")
        self.root.update()

        try:
            # 1. Gather and Validate Input
            symbol_str = self.symbols_var.get().upper()
            start_date_str = self.start_date_var.get()
            end_date_str = self.end_date_var.get()
            
            symbols_list = [s.strip() for s in symbol_str.split(',') if s.strip()]
            if not symbols_list:
                raise ValueError("Please enter at least one valid stock symbol.")
            
            # 2. Call the Financial Calculation
            df_normalized = calculate_normalized_return(symbols_list, start_date_str, end_date_str)
            
            # --- START: New logic to print initial values to console ---
            print("\n--- Initial Normalized Values (Investment Required to reach $1.00 at End) ---")
            
            # The initial value is the first row (iloc[0]) of the normalized DataFrame
            initial_values = df_normalized.iloc[0]
            
            for symbol, initial_value in initial_values.items():
                print(f"{symbol}: ${initial_value:.4f}")
            
            print("----------------------------------------------------------------------------------")

            # 3. Update the Plot
            self.ax.clear()
            
            for column in df_normalized.columns:
                self.ax.plot(df_normalized.index, df_normalized[column], label=column, linewidth=0.5)

            self.ax.set_title(f"Normalized Performance ({start_date_str} to {end_date_str})")
            self.ax.set_xlabel("Date")
            self.ax.set_ylabel("Normalized Asset Worth (End Value = $1.00)")
            self.ax.legend(title='Symbol', loc='upper left')
            self.ax.grid(True, linestyle='--', alpha=0.7)
            
            # Ensure Y-axis starts near zero and ends near 1
            y_min = df_normalized.min().min() * 0.95
            y_max = df_normalized.max().max() * 1.05
            self.ax.set_ylim([max(0, y_min), y_max])

            self.fig.autofmt_xdate() # Format x-axis dates nicely
            self.canvas.draw()
            
        except ValueError as e:
            # Handle specific known errors (e.g., input validation, data not found)
            messagebox.showerror("Input Error / Data Fetch Error", str(e))
        except Exception as e:
            # Handle general unexpected errors (e.g., network issues)
            messagebox.showerror("Unexpected Error", f"An unexpected error occurred: {e}")
            
        finally:
            self.run_button.config(state=tk.NORMAL, text="Run Analysis & Plot")

if __name__ == '__main__':
    # Initialize the main Tkinter window
    root = tk.Tk()
    app = StockAnalyzerApp(root)
    # Start the Tkinter event loop
    root.mainloop()
