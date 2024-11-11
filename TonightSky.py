import sys
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
from tkinter import filedialog
from datetime import datetime, date, timedelta, time
import pytz
from timezonefinder import TimezoneFinder
import csv
import webbrowser
import json
import os
import platform
from astropy.coordinates import EarthLocation, AltAz, SkyCoord
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import get_sun
import threading
import urllib.parse
import webbrowser
import re
import shutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.collections import LineCollection
import matplotlib.dates as mdates 
import numpy as np
#from scipy.interpolate import CubicSpline
from astroplan import Observer, FixedTarget


# Define files the JSON file is where the sesttings and CSV path will be stored 
# if not find in app folder
json_file = 'tonightsky.json'
csv_filename = 'celestial_catalog.csv'  # The default CSV file name

def load_settings():
    """Load settings from tonightsky.json, including filters and catalog checkboxes."""
    settings_path = get_app_data_path(json_file)
    if os.path.exists(settings_path):
        with open(settings_path, 'r') as file:
            return json.load(file)
    return {
        "latitude": "-33.713611", 
        "longitude": "151.090278", 
        "date": datetime.now().strftime("%Y-%m-%d"),
        "local_time": "22:00", 
        "timezone": "Australia/Sydney",
        "filter_expression": "altitude > 30 AND transit time < 02",
        "catalogs": {"Messier": True, "NGC": True, "IC": False, "Caldwell": False, "Abell": False, "Sharpless": False}
    }

def save_settings(settings):
    """Save settings to tonightsky.json, including filters."""
    settings_path = get_app_data_path(json_file)
    with open(settings_path, 'w') as file:
        json.dump(settings, file, indent=4)

def get_app_data_path(filename):
    """Get the path to store files like settings and CSV in a platform-appropriate folder."""
    if platform.system() == 'Windows':
        # Use AppData on Windows
        appdata = os.getenv('APPDATA')
        app_data_dir = os.path.join(appdata, 'TonightSky')
    elif platform.system() == 'Darwin':
        # Use Library/Application Support on macOS
        home = os.path.expanduser('~')
        app_data_dir = os.path.join(home, 'Library', 'Application Support', 'TonightSky')
    else:
        # Use ~/.tonightsky on Linux/other platforms
        app_data_dir = os.path.join(os.path.expanduser("~"), '.tonightsky')

    os.makedirs(app_data_dir, exist_ok=True)  # Ensure the directory exists
    return os.path.join(app_data_dir, filename)

def get_csv_path():
    """Check if CSV exists in the csv_path_entry, then verify, or fallback to other methods."""
    # Step 1: Check if the CSV file exists in the same folder as the Python script (debugging/development environment)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_csv_path = os.path.join(script_dir, csv_filename)

    if os.path.exists(script_csv_path):
        return script_csv_path

    # Step 2: Check if the CSV file exists in the app data folder
    csv_data_path = get_app_data_path(csv_filename)
    if os.path.exists(csv_data_path):
        return csv_data_path

    # Step 3: Check if we're running inside a PyInstaller bundle (_MEIPASS)
    if hasattr(sys, '_MEIPASS'):
        bundled_csv_path = os.path.join(sys._MEIPASS, csv_filename)
        if os.path.exists(bundled_csv_path):
            shutil.copy(bundled_csv_path, csv_data_path)
            return csv_data_path

    # Step 4: If not found, prompt the user to select the CSV file manually
    csv_file_path = filedialog.askopenfilename(
        title="Select the celestial catalog CSV file",
        filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
    )

    if not csv_file_path:
        print("Error: No file selected.")
        sys.exit(1)

    # Copy the selected CSV file to the app data folder
    shutil.copy(csv_file_path, csv_data_path)
    return csv_data_path

# Convert Right Ascension from degrees to RA in HH:MM:SS format
def degrees_to_ra(degrees):
    hours = int(degrees // 15)
    minutes = int((degrees % 15) * 4)
    seconds = (degrees % 15) * 240 - minutes * 60
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d}"

# Convert Declination to a formatted string
def format_dec(dec):
    return f"{dec:.2f}°"

def format_transit_time(transit_time_minutes):
    """
    Formats the transit time in minutes to HH:MM:SS or MM:SS.
    :param transit_time_minutes: The transit time in minutes.
    :return: A formatted time string.
    """
    time_to_transit_seconds = abs(transit_time_minutes * 60)
    
    # Calculate hours, minutes, and seconds
    hours = int(time_to_transit_seconds // 3600)
    minutes = int((time_to_transit_seconds % 3600) // 60)
    seconds = int(time_to_transit_seconds % 60)

    # Return formatted string as HH:MM:SS always
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Calculate Local Sidereal Time (LST)
def calculate_lst(longitude, utc_time):
    astropy_time = Time(utc_time)
    lst = astropy_time.sidereal_time('mean', longitude * u.deg).hour
    return lst

# Function to calculate transit time and AltAz using astropy
def calculate_transit_and_alt_az(ra_deg, dec_deg, latitude, longitude, local_time):
    # Create astropy Time object in UTC
    astropy_time = Time(local_time.astimezone(pytz.utc))
    
    # Define the observer's location using astropy's EarthLocation
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg, height=0 * u.m)
    
    # Create a SkyCoord object for the celestial object (RA/Dec)
    target = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg)
    
    # Create an AltAz object for the observer's location and time
    altaz = AltAz(obstime=astropy_time, location=location)
    
    # Calculate the Altitude and Azimuth of the target
    altaz_coord = target.transform_to(altaz)
    altitude = altaz_coord.alt.deg
    azimuth = altaz_coord.az.deg

    # Calculate Local Sidereal Time (LST)
    lst = astropy_time.sidereal_time('mean', longitude * u.deg).hour

    # Transit occurs when the LST matches the RA of the object
    ra_hours = ra_deg / 15.0
    time_diff_hours = ra_hours - lst

    # Ensure the time difference is within the range [-12, +12] hours
    if time_diff_hours > 12:
        time_diff_hours -= 24
    elif time_diff_hours < -12:
        time_diff_hours += 24

    # Determine whether it's Before or After the transit time
    if time_diff_hours >= 0:
        before_after = "After"
    else:
        before_after = "Before"

    # Convert the time difference to minutes
    transit_time_minutes = abs(time_diff_hours * 60)  # Use absolute value for relative time

        # Calculate local transit time using timedelta from current local time
    local_transit_time = local_time + timedelta(minutes=transit_time_minutes if before_after == "After" else -transit_time_minutes)

    return transit_time_minutes, local_transit_time.strftime("%H:%M:%S"), before_after, altitude, azimuth

def parse_query_conditions(query, valid_columns):
    """Parse the query and validate column names against valid columns."""
    
    # Regex to capture the column name (which may include spaces), operator (including LIKE), value, and logical operators (AND, OR, +, |)
    pattern = r"([a-zA-Z_][\w\s]*)\s*(>|>=|<|<=|=|!=|like)\s*('[^']*'|\"[^\"]*\"|[\w\.]+)\s*(AND|OR|\+|\|)?"
    
    conditions = []
    for match in re.finditer(pattern, query, re.IGNORECASE):
        column, operator, value, logic_op = match.groups()
        column = column.lower().strip()  # Normalize column name to lowercase and strip spaces

        if column in valid_columns:
            # Prepare the structure for execution later, storing the valid column, operator, and value
            conditions.append((valid_columns[column], operator, value.strip("'\""), logic_op))
        else:
            raise ValueError(f"Invalid column: {column}")

    return conditions

def evaluate_conditions(row, conditions):
    """Evaluate the parsed conditions on a given row of data, including support for 'LIKE' operator on strings."""
    if not conditions:
        return True  # If no conditions, consider the row valid (no filtering)

    for column, operator, value, logic_op in conditions:
        row_value = row[column]

        # Perform type conversions and handle degree symbol if present
        row_value = row_value.strip('°')  # Remove degree symbol if present

        # Attempt to convert both row_value and value to float if they are numeric
        def is_numeric(value):
            """Check if a value can be converted to a float."""
            try:
                float(value)
                return True
            except ValueError:
                return False

        if is_numeric(row_value) and is_numeric(value):
            row_value = float(row_value)
            value = float(value)
        else:
            # Convert both values to lowercase strings for string comparisons
            row_value = str(row_value).lower()
            value = str(value).lower()

        # Perform comparison based on the operator
        if operator == '>' and not row_value > value:
            return False
        elif operator == '>=' and not row_value >= value:
            return False
        elif operator == '<' and not row_value < value:
            return False
        elif operator == '<=' and not row_value <= value:
            return False
        elif operator == '=' and not row_value == value:
            return False
        elif operator == '!=' and not row_value != value:
            return False
        elif operator == 'like':
            if isinstance(row_value, str) and value in row_value:  # Ensure LIKE is only used with strings
                continue
            else:
                return False  # If not a string or no match, condition fails

    return True  # If all conditions pass, return True

def calculate_sunset_sunrise(latitude, longitude, date, timezone_str):
    """Calculates the sunset and sunrise times for a given location and date.

    Args:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
        date: Date as a datetime.date object.
        timezone_str: Timezone string (e.g., 'Australia/Sydney').

    Returns:
        A tuple of datetime objects representing sunset and sunrise times, respectively.
    """

    # Convert date to a datetime at midnight for Astropy Time
    date_with_time = datetime.combine(date, time(0, 0))  # Use 'time' from 'datetime'

    time_obj = Time(date_with_time, scale='utc')  # Using a datetime object

    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    timezone = pytz.timezone(timezone_str)
    observer = Observer(location=location, timezone=timezone)

    # Calculate sunset and sunrise times
    sunset_time = observer.sun_set_time(time_obj, which='nearest').to_datetime(timezone)
    sunrise_time = observer.sun_rise_time(time_obj, which='next').to_datetime(timezone)

    return sunset_time, sunrise_time
    
# Function to calculate astronomical dusk and dawn
def calculate_astronomical_dusk_dawn(latitude, longitude, date, timezone_str):
    """Calculates the times for astronomical dusk and dawn on a given date and location.

    Args:
        latitude: Latitude in degrees.
        longitude: Longitude in degrees.
        date: Date as a datetime object.
        timezone_str: Timezone string (e.g., 'US/Eastern').

    Returns:
        A tuple of datetime objects representing dusk and dawn times, respectively.
    """

    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    timezone = pytz.timezone(timezone_str)

    # Create an Observer object
    observer = Observer(location=location, timezone=timezone)

    # Calculate local midnight in UTC
    date_midnight_utc = Time(datetime.combine(date, datetime.min.time()), scale='utc')

    # Define dusk and dawn altitude
    dusk_dawn_altitude = -18 * u.deg

    # Use Observer methods to directly calculate dusk and dawn
    dusk_time = observer.sun_set_time(date_midnight_utc, which='next', horizon=dusk_dawn_altitude).to_datetime(timezone)
    dawn_time = observer.sun_rise_time(date_midnight_utc, which='next', horizon=dusk_dawn_altitude).to_datetime(timezone)

    return dusk_time, dawn_time

def generate_altitude_data(ra_deg, dec_deg, latitude, longitude, date, timezone_str, dusk_time, dawn_time):
    """Generate altitude data for a celestial object from half an hour before dusk to half an hour after dawn."""
    
    # Observer location and target
    location = EarthLocation(lat=latitude * u.deg, lon=longitude * u.deg)
    target = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg)
    
    # Define start and end times based on dusk and dawn (already localized)
    start_time = dusk_time - timedelta(minutes=30)
    end_time = dawn_time + timedelta(minutes=30)
    
    # Generate list of times in 10-minute intervals, converting to UTC for astropy handling
    times = [start_time + timedelta(minutes=10) * i for i in range(int((end_time - start_time).total_seconds() / 600) + 1)]
    times_utc = [t.astimezone(pytz.UTC) for t in times]  # Convert to UTC
    astropy_times = Time(times_utc)
    
    # Transform the target coordinates to AltAz for each time interval
    altaz_frame = AltAz(obstime=astropy_times, location=location)
    altitudes = target.transform_to(altaz_frame).alt.deg
    
    # Pair times and altitudes in local time for the final output
    altitude_data = [(t, alt) for t, alt in zip(times, altitudes)]
    
    return altitude_data

def plot_altitude_graph(object_name, altitude_data, transit_time, dusk_time, dawn_time):
    """Plot the altitude vs time graph with night shading and vertical lines for transit and midnight."""
    times, altitudes = zip(*altitude_data)

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot altitude data with color coding for day and night
    for i in range(1, len(times)):
        start_time, end_time = times[i-1], times[i]
        start_alt, end_alt = altitudes[i-1], altitudes[i]
        color = "blue" if start_time < dusk_time or start_time > dawn_time else "white"
        ax.plot([start_time, end_time], [start_alt, end_alt], color=color)

    # Shade for night time
    ax.axvspan(times[0], dusk_time, color="lightgrey", alpha=0.5, label="Twilight")
    ax.axvspan(dawn_time, times[-1], color="lightgrey", alpha=0.5)
    ax.axvspan(dusk_time, dawn_time, color="black", alpha=0.8, label="Night")

    # Add vertical lines for transit and midnight
    ax.axvline(x=transit_time, color="red", linestyle="--", linewidth=1, label="Transit")
    midnight = times[0].replace(day=times[0].day + 1, hour=0, minute=0)
    ax.axvline(x=midnight, color="yellow", linestyle="--", linewidth=1, label="Midnight")

    # Horizontal lines for altitude reference
    for y in range(10, 91, 10):
        line_color = "white" if dusk_time < times[0] < dawn_time else "grey"
        ax.axhline(y=y, color=line_color, linestyle="--", linewidth=0.5)

    # Format plot
    ax.set_xlim([times[0], times[-1]])
    ax.set_ylim(0, 90)
    ax.set_title(f"{object_name} Altitude vs Time (Transit at {transit_time.strftime('%H:%M')})")
    ax.set_xlabel("Local Time")
    ax.set_ylabel("Altitude (degrees)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=dusk_time.tzinfo))
    ax.legend(loc="upper left")
    plt.xticks(rotation=45)

    # Center the plot window on the screen
    root = tk.Tk()
    root.withdraw()  # Hide the root Tkinter window

    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Define plot window size
    plot_width = 800
    plot_height = 400

    # Calculate the position to center the window
    x = (screen_width - plot_width) // 2
    y = (screen_height - plot_height) // 2

    # Set the window position
    fig.canvas.manager.window.wm_geometry(f"{plot_width}x{plot_height}+{x}+{y}")

    plt.show(block=False)
    root.destroy()  # Destroy the Tkinter root after plotting

# GUI Application Class
class TonightSkyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TonightSky Object Transit Calculator (v1.5)")
        # Initialize the abort flag
        self.abort_flag = threading.Event()

        # Load saved settings (including filters)
        self.settings = load_settings()

         # Set initial window size
        window_width = 1300
        window_height = 1000
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Configure grid columns and rows for the desired layout
        self.root.grid_columnconfigure(0, weight=0)  # Column for labels
        self.root.grid_columnconfigure(1, weight=0)  # Column for entry widgets
        self.root.grid_columnconfigure(2, weight=0)  # Column for "List Objects" button, etc.
        self.root.grid_columnconfigure(3, weight=1)  # Column for "Data Path" entry, will expand
        self.root.grid_columnconfigure(4, weight=0)  # Column for "Browse" button
        self.root.grid_rowconfigure(9, weight=1)  # Allow the row with the Treeview to expand

        # Latitude and Longitude inputs
        tk.Label(root, text="Latitude:").grid(row=0, column=0, sticky="w")
        self.lat_entry = tk.Entry(root, width=15)
        self.lat_entry.grid(row=0, column=1, sticky="ew")
        self.lat_entry.insert(0, self.settings.get("latitude", "-33.713611"))

        tk.Label(root, text="Longitude:").grid(row=1, column=0, sticky="w")
        self.lon_entry = tk.Entry(root, width=15)
        self.lon_entry.grid(row=1, column=1, sticky="ew")
        self.lon_entry.insert(0, self.settings.get("longitude", "151.090278"))

        # Date input
        tk.Label(root, text="Date (yyyy-mm-dd):").grid(row=2, column=0, sticky="w")
        self.date_entry = tk.Entry(root, width=15)
        self.date_entry.grid(row=2, column=1, sticky="ew")
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Local Time input
        tk.Label(root, text="Local Time (24h):").grid(row=3, column=0, sticky="w")
        self.time_entry = tk.Entry(root, width=15)
        self.time_entry.grid(row=3, column=1, sticky="ew")
        self.time_entry.insert(0, self.settings.get("local_time", "22:00"))

        # Timezone dropdown list
        tk.Label(root, text="Timezone:").grid(row=4, column=0, sticky="w")
        latitude = float(self.lat_entry.get())
        longitude = float(self.lon_entry.get())
        tf = TimezoneFinder()
        default_timezone = tf.timezone_at(lat=latitude, lng=longitude)
        if not default_timezone:
            default_timezone = 'Australia/Sydney'
        timezones = pytz.all_timezones
        self.timezone_combobox = ttk.Combobox(root, values=timezones, width=25)
        self.timezone_combobox.grid(row=4, column=1, sticky="ew")
        self.timezone_combobox.set(self.settings.get("timezone", default_timezone))

        # Data Path label and entry
        tk.Label(root, text="Data Path:").grid(row=0, column=2, sticky="w") 
        self.csv_path_entry = tk.Entry(root, width=50)
        self.csv_path_entry.grid(row=0, column=3, sticky="ew")
        self.csv_path_entry.insert(0, self.settings.get('csv_file_path', ''))

        # Check if the csv_path_entry is empty, if so, call get_csv_path
        if not self.csv_path_entry.get():
            self.csv_path_entry.insert(0, get_csv_path())
        
        # Browse button for the Data Path
        self.browse_button = tk.Button(root, text="Browse", command=self.browse_csv_file)
        self.browse_button.grid(row=0, column=4, sticky="w")

        # List Objects button
        self.list_button = tk.Button(root, text="List Objects", command=self.toggle_search, width=12)
        self.list_button.grid(row=4, column=2, sticky="w")

        # Sidereal Time label and value
        tk.Label(root, text="Sidereal Time:").grid(row=3, column=2, padx=5, sticky="w")
        self.sidereal_value_label = tk.Label(root, text="")  # Value label for sidereal time
        self.sidereal_value_label.grid(row=3, column=3, sticky="w")
        self.initialize_sidereal_time()

        # Bind events to recalculate Sidereal Time
        self.lat_entry.bind("<KeyRelease>", self.update_sidereal_time)
        self.lon_entry.bind("<KeyRelease>", self.update_sidereal_time)
        self.time_entry.bind("<KeyRelease>", self.update_sidereal_time)


        # Check Box setup for catalogs (load saved checkbox states)
        self.catalog_vars = {
            "Messier": tk.BooleanVar(),
            "NGC": tk.BooleanVar(),
            "IC": tk.BooleanVar(),
            "Caldwell": tk.BooleanVar(),
            "Abell": tk.BooleanVar(),
            "Sharpless": tk.BooleanVar()
        }

        # Restore saved checkbox states
        saved_catalogs = self.settings.get("catalogs", {})
        for catalog, var in self.catalog_vars.items():
            var.set(saved_catalogs.get(catalog, False))  # Set the saved state, default to False if not present

        row, col = 5, 0 
        for i, (catalog, var) in enumerate(self.catalog_vars.items()):
            chk = tk.Checkbutton(root, text=catalog, variable=var)
            chk.grid(row=row, column=col, sticky="w") # Place checkboxes in column 0
            row += 1
            if row > 7:
                row, col = 5, col + 1  # Move to the next column if needed

        # Add the multi-line filter edit control
        tk.Label(root, text="Enter Filter ('altitude > 30'):").grid(row=8, column=0, sticky="w", pady=(5, 0))
        self.query_text = tk.Text(root, height=4, width=100)
        self.query_text.grid(row=9, column=0, columnspan=7, sticky="ew", pady=(5, 5))
        self.query_text.insert(tk.END, self.settings.get("filter_expression", "altitude > 30 and transit time < 02"))
        self.root.grid_rowconfigure(9, weight=0)  # Ensure edit control does not expand vertically
        self.query_text.bind("<Control-Return>", lambda event: self.list_objects())

        # Treeview for displaying objects
        columns = ("Name", "RA", "Dec", "Transit Time", "Relative TT", "Before/After", "Altitude", "Azimuth", "Alt Name", "Type", "Magnitude", "Info", "Catalog")
        tree_frame = tk.Frame(root)
        tree_frame.grid(row=10, column=0, columnspan=7, sticky="nsew", pady=(5, 5))
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_column(_col, False))
            self.tree.column(col, width=100, minwidth=100)
        self.root.grid_rowconfigure(10, weight=1)

        # Status Label
        self.status_label = tk.Label(root, text="Ready", anchor="w")
        self.status_label.grid(row=11, column=0, columnspan=7, sticky="ew")
        self.root.grid_rowconfigure(11, weight=0)

        # Bind the resize event
        self.bind_treeview_selection()
        self.create_context_menu()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.figure = None


    def get_csv_path(self):
        """Class method that checks the csv_path_entry and returns the path, or calls external get_csv_path."""
        csv_path = self.csv_path_entry.get()
        if csv_path and os.path.exists(csv_path):
            return csv_path
        else:
            # Call the external get_csv_path function
            return get_csv_path()
    
    def browse_csv_file(self):
        """Prompt the user to select a CSV file."""
        csv_file_path = filedialog.askopenfilename(
            title="Select the celestial catalog CSV file",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )
        if csv_file_path:
            self.csv_path_entry.delete(0, tk.END)
            self.csv_path_entry.insert(0, csv_file_path)
            self.settings['csv_file_path'] = csv_file_path
            self.save_settings()


    # Handle treeview resize to adjust Min/Max fields width
    #def on_treeview_resize(self, event):
    #    pass

    # Sorting column function
    def sort_column(self, col, reverse):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        data.sort(reverse=reverse)
        for index, (_, k) in enumerate(data):
            self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))


# List_Objects becomes CAncel button while search in progress
    def toggle_search(self):
        """Toggle between starting and canceling the search."""
        if self.list_button.cget("text") == "List Objects":
            # Start search
            self.abort_flag.clear()
            self.list_button.config(text="Cancel")
            self.list_objects()
        else:
            # Cancel search
            self.abort_flag.set()
            self.list_button.config(text="List Objects")
            self.update_status("Search canceled")

    def cancel_search(self):
        """Signal the search to abort."""
        self.abort_flag.set()  # Set the abort flag to True
        self.update_status("Cancelling search...")
        self.list_button.config(text="List Objects", state=tk.NORMAL)  # Restore the button text and functionality

    def restore_list_button(self):
        """Restore the List Objects button to its default state."""
        
        self.list_button.config(text="List Objects", state=tk.NORMAL, command=self.toggle_search)
        self.update_status("Ready")  # Reset the status label to indicate readiness

    ################################################################
    # Load objects and calculate AltAz and transit time
    def list_objects(self):
        """Handle the listing of celestial objects based on user input and query conditions."""
        # Remove focus from the query text field and set it on the Treeview
        self.tree.focus_set()

        # Get the current query from the text box
        query = self.query_text.get("1.0", tk.END).strip()  # Read the entered query from the edit control

        # Get valid column names from the Treeview (in lowercase for case-insensitive comparison)
        valid_columns = {col.lower(): col for col in self.tree["columns"]}

        # Parse the query conditions, if any
        try:
            conditions = parse_query_conditions(query, valid_columns) if query else []
        except ValueError as e:
            self.update_status(f"Error: {e}")  # Display parsing error in the status label
            self.list_button.config(state=tk.NORMAL)
            return
            # Get the CSV file path
        file_path = self.get_csv_path()


        # Start the worker thread to load objects in the background, passing the parsed conditions
        thread = threading.Thread(target=self.load_objects_in_background, args=(file_path, conditions,))
        thread.start()
    

    def load_objects_in_background(self, file_path, conditions):
        """Load objects in a background thread, apply parsed conditions, and update the progress."""
        # Get user input values
        latitude = float(self.lat_entry.get())
        longitude = float(self.lon_entry.get())
        local_time_str = self.time_entry.get()

        # Determine local timezone based on latitude and longitude using TimezoneFinder
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

        if timezone_str:
            timezone = pytz.timezone(timezone_str)
            # Update the combobox with the found timezone
            self.timezone_combobox.set(timezone_str)
        else:
            self.update_status("Timezone not found for the given coordinates")
            self.list_button.config(state=tk.NORMAL)
            return

        # Convert input local time and date to a datetime object using the found timezone
        try:
            today_str = self.date_entry.get()
            local_date_time = f"{today_str} {local_time_str}"  # Combine date and time
            local_time = timezone.localize(datetime.strptime(local_date_time, "%Y-%m-%d %H:%M"))
        except ValueError:
            self.update_status("Invalid Date or Time format")
            self.list_button.config(state=tk.NORMAL)
            return

        # Get selected catalogs for filtering
        filters = [key for key, var in self.catalog_vars.items() if var.get()]

        # Update the status label to show "Loading..."
        self.status_label.config(text="Loading...")
        self.root.update_idletasks()  # Ensure immediate UI update

        # Function to update the progress
        def update_progress(progress_percentage):
            self.root.after(0, lambda: self.status_label.config(text=f"Loading... {progress_percentage}%"))

        # Load the objects (in the background thread), applying conditions and updating progress
        objects = self.list_objects_near_transit(file_path, latitude, longitude, local_time, filters, conditions, progress_callback=update_progress)

        # Update the Treeview with the loaded objects (back on the main thread)
        self.root.after(0, lambda: self.update_treeview(objects))

        # Once done, update status to "Search complete" and enable the List button and query edit box
        self.root.after(0, lambda: self.status_label.config(text="Search complete"))
        self.root.after(0, lambda: self.query_text.config(state=tk.NORMAL))  # Re-enable the query text box
        # Restore the List Objects button and status after completion
        self.root.after(0, lambda: self.restore_list_button())

    def update_status(self, message):
        """Update the status label at the bottom of the window."""
        self.status_label.config(text=message)

    def list_objects_near_transit(self, file_path, latitude, longitude, local_time, filters, conditions, progress_callback=None):
        """
        Load objects from CSV file, calculate their transit times and alt/az, and apply query conditions.
        Updates progress after evaluating each row.
        """
        objects = []

        with open(file_path, mode='r', encoding='ISO-8859-1') as file:
            reader = csv.DictReader(file)
            total_rows = sum(1 for _ in file) - 1  # Total number of rows, excluding header
            file.seek(0)  # Reset file pointer to the beginning after counting rows
            processed_rows = 0

            # Convert local time to UTC and calculate Local Sidereal Time (LST)
            utc_time = local_time.astimezone(pytz.utc)
            lst = calculate_lst(longitude, utc_time)

            for row in reader:
                # Check for abort signal
                if self.abort_flag.is_set():
                    break  # Exit the loop if the user cancels the search

                # Update progress regardless of whether the row passed or failed the conditions
                processed_rows += 1
                if processed_rows % 100 == 0:
                    progress_percentage = int((processed_rows / total_rows) * 100)
                    if progress_callback:
                        progress_callback(progress_percentage)

                catalog = row['Catalog'].strip()
                if filters and catalog not in filters:
                    continue

                try:
                    ra = float(row['RA'])  # Assuming RA is in hours
                    dec = float(row['Dec'])  # Assuming Dec is in degrees
                except ValueError:
                    continue  # Skip rows with invalid RA/Dec values

                # Step 1: Compute values like transit time, altitude, and azimuth
                #transit_time_minutes, before_after, altitude, azimuth = calculate_transit_and_alt_az(ra, dec, latitude, longitude, local_time)
                transit_time_minutes, local_transit_time, before_after, altitude, azimuth = calculate_transit_and_alt_az(ra, dec, latitude, longitude, local_time)

                # Skip objects with negative altitude (below horizon)
                if altitude < 0:
                    continue


                # Step 2: Build the complete row object (from both CSV and computed values)
                current_row = {
                    'Name': row['Name'],
                    'RA': degrees_to_ra(float(row['RA'])),
                    'Dec': format_dec(dec),
                    'Transit Time': local_transit_time,
                    'Relative TT': format_transit_time(transit_time_minutes),
                    'Before/After': before_after,
                    'Altitude': f"{altitude:.2f}°",
                    'Azimuth': f"{azimuth:.2f}°",
                    'Alt Name': row['Alt Name'],
                    'Type': row['Type'],
                    'Magnitude': row['Magnitude'],
                    'Info': row['Info'],
                    'Catalog': row['Catalog']
                }


                # Step 3: Evaluate conditions on the fully built row object
                if evaluate_conditions(current_row, conditions):
                    # Append the object details to the final list if the conditions are met
                    objects.append(current_row)


        return objects


    def update_treeview(self, objects):
        """Update the Treeview with the loaded celestial objects."""
        # Clear the treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Populate the treeview with the filtered objects
        for obj in objects:
            self.tree.insert("", "end", values=(obj['Name'], obj['RA'], obj['Dec'],
                                                obj['Transit Time'], obj['Relative TT'], 
                                                obj['Before/After'], obj['Altitude'], obj['Azimuth'], 
                                                obj['Alt Name'], obj['Type'], obj['Magnitude'], 
                                                obj['Info'], obj['Catalog']))

        # Enable the list button again and update status
        self.list_button.config(state=tk.NORMAL)
        self.update_status("Search complete")


    def save_settings(self):
        """Save settings to tonightsky.json."""
        settings = {
            "latitude": self.lat_entry.get(),
            "longitude": self.lon_entry.get(),
            "date": self.date_entry.get(),
            "local_time": self.time_entry.get(),
            "timezone": self.timezone_combobox.get(),
            "filter_expression": self.query_text.get("1.0", tk.END).strip(),
            "catalogs": {catalog: var.get() for catalog, var in self.catalog_vars.items()},
            "csv_file_path": self.csv_path_entry.get()  # Save the CSV file path
        }
        save_settings(settings)

    def update_sidereal_time(self, event=None):
        """Update Sidereal Time based on the current input values."""
        self.initialize_sidereal_time()
        
    def initialize_sidereal_time(self):
        """Initialize Sidereal Time based on the current input values."""
        try:
            longitude = float(self.lon_entry.get())
            local_time_str = self.time_entry.get()
            date_str = self.date_entry.get()
            timezone_str = self.timezone_combobox.get()
            local_time = datetime.strptime(f"{date_str} {local_time_str}", "%Y-%m-%d %H:%M")
            timezone = pytz.timezone(timezone_str)
            local_time = timezone.localize(local_time)
            utc_time = local_time.astimezone(pytz.utc)
            lst_hours = calculate_lst(longitude, utc_time)
            hours = int(lst_hours)
            minutes = int((lst_hours * 60) % 60)
            seconds = int((lst_hours * 3600) % 60)
            lst_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.sidereal_value_label.config(text=lst_formatted)  # Update the sidereal value label
        except Exception as e:
            self.sidereal_value_label.config(text="Error")
            print(f"Error in Sidereal Time calculation: {e}")

    def copy_to_clipboard(self):
        """Copy the content of the selected item in the Treeview to the clipboard."""
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            item_values = item['values']

            headers = ["Name", "RA", "Dec", "Transit Time", "Before/After", "Altitude", "Azimuth", "Alt Name", "Type", "Magnitude", "Info", "Catalog"]
            formatted_text = '\t'.join(headers) + '\n'
            formatted_text += '\t'.join(map(str, item_values))

            self.root.clipboard_clear()
            self.root.clipboard_append(formatted_text)

            self.status_label.config(text="Selected item copied to clipboard!")

    def bind_treeview_selection(self):
        """Bind the selection event of the Treeview to copy content to clipboard."""
        self.tree.bind("<<TreeviewSelect>>", lambda event: self.copy_to_clipboard())
        # Bind the double-click event to open the Astrobin page
        self.tree.bind("<Double-1>", lambda event: self.open_astrobin_page())


    # List context menu
    def create_context_menu(self):
        """Create the right-click context menu for the Treeview."""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Graph", command=self.open_altitude_graph)
        self.context_menu.add_command(label="Copy", command=self.copy_to_clipboard)
        if platform.system() == 'Darwin':
            self.tree.bind("<Control-Button-1>", self.show_context_menu)
            self.tree.bind("<Button-2>", self.show_context_menu)
        else:
            self.tree.bind("<Button-3>", self.show_context_menu)


    def show_context_menu(self, event):
        """Show the context menu on right-click."""
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.context_menu.post(event.x_root, event.y_root)
        else:
            self.tree.selection_remove(self.tree.selection())
            self.context_menu.post(event.x_root, event.y_root)

    def open_astrobin_page(self):
        """Open AstroBin search page for the selected object."""
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            object_name = item['values'][0]  # Extract the name of the selected object

            # Generate the AstroBin search URL based on the object name
        # Remove spaces and encode the object name for a URL
            object_name_url = urllib.parse.quote(object_name.replace(' ', ''))
            url = f"https://www.astrobin.com/search/?q={object_name_url}"
            webbrowser.open(url)
   
    def on_exit(self):
        """Save settings on exit."""
        self.save_settings()
        self.root.destroy()

    # Update open_altitude_graph function
    def open_altitude_graph(self):
        """Generate an altitude graph for the selected object."""
        selected_item = self.tree.selection()
        if selected_item:
            item = self.tree.item(selected_item)
            object_name = item['values'][0]
            dec = float(item['values'][2].strip('°'))
            latitude = float(self.lat_entry.get())
            longitude = float(self.lon_entry.get())
            timezone_str = self.timezone_combobox.get()

            # Extract hours, minutes, and seconds from the RA string
            ra_parts = item['values'][1].split(':')
            ra_hours = float(ra_parts[0])
            ra_minutes = float(ra_parts[1])
            ra_seconds = float(ra_parts[2]) if len(ra_parts) > 2 else 0.0

            # Convert RA to degrees, including minutes and seconds
            ra = (ra_hours + ra_minutes / 60 + ra_seconds / 3600) * 15

            # Extract and parse the transit time (already in local time)
            transit_time_str = item['values'][3]
            try:
                transit_time = datetime.strptime(transit_time_str, "%H:%M:%S")
            except ValueError:
                transit_time = datetime.strptime(transit_time_str, "%H:%M")

            # Use the date from the date entry control
            date_str = self.date_entry.get()
            selected_date = datetime.strptime(date_str, "%Y-%m-%d")

            # Adjust date for transit time if necessary
            day = selected_date.day + 1 if transit_time.hour < 12 else selected_date.day
            timezone = pytz.timezone(timezone_str)
            transit_time = timezone.localize(
                transit_time.replace(year=selected_date.year, month=selected_date.month, day=day)
            )

            # Calculate sunset and sunrise for the selected date
            sunset, sunrise = calculate_sunset_sunrise(latitude, longitude, selected_date.date(), timezone_str)
            # Generate altitude data using dusk and dawn times
            altitude_data = generate_altitude_data(ra, dec, latitude, longitude, selected_date.date(), timezone_str, sunset, sunrise)

            # Calculate dusk and dawn times for the selected date
            dusk_time, dawn_time = calculate_astronomical_dusk_dawn(latitude, longitude, selected_date.date(), timezone_str)

            # Call the plot function
            plot_altitude_graph(object_name, altitude_data, transit_time, dusk_time, dawn_time)

    def on_closing(self):
        """Close the main app and any open plot windows."""
        plt.close('all')  # Close all matplotlib plot windows
        self.root.destroy()  # Close the Tkinter window

# Main entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = TonightSkyApp(root)
    root.mainloop()
