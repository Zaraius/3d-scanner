import serial
import matplotlib.pyplot as plt
import math
import time
import datetime
import argparse
import csv
import os

# --- 1. Configuration ---
# IMPORTANT: Change this to the correct serial port for your computer!
# On Windows, it will be "COM3", "COM4", etc.
# On Mac/Linux, it will be "/dev/tty.usbmodemXXXX" or "/dev/ttyACM0", etc.
ARDUINO_COM_PORT = "/dev/ttyACM0" 
BAUD_RATE = 115200 # Must match the rate in the Arduino code

# Parse CLI args to allow CSV input
parser = argparse.ArgumentParser(description="3D scan visualizer (live serial or CSV)")
parser.add_argument('--csv-file', '-c', help='Path to CSV file containing pan,tilt,duration lines (use instead of live serial)')
args = parser.parse_args()
CSV_FILE = args.csv_file

# --- 2. Calibration Function ---
# This function uses the slope and intercept from your sensor_plots.py script.
# It converts the raw `duration` value from the sensor into inches.
def get_calibrated_distance_inches(duration):
    slope = 0.0069
    intercept = -0.0751
    # Handle cases where the sensor returns 0 (no echo)
    if duration == 0:
        return 0 # A reading of 0 means the point is invalid
    return slope * duration + intercept

# --- 3. Setup Serial Connection and Plot ---
ser = None
if not CSV_FILE:
    try:
        ser = serial.Serial(ARDUINO_COM_PORT, BAUD_RATE, timeout=5)
        time.sleep(5)
        print(f"Connected to Arduino on {ARDUINO_COM_PORT}")
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {ARDUINO_COM_PORT}.")
        print(f"Details: {e}")
        exit()
else:
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file not found: {CSV_FILE}")
        exit()
    print(f"Reading data from CSV: {CSV_FILE}")

# Setup the 3D plot
plt.ion() # Turn on interactive mode for live plotting
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')

# Lists to store the cartesian coordinates of the scanned points
points = []

# If CSV mode, load lines into memory
csv_lines = []
if CSV_FILE:
    with open(CSV_FILE, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            # Row may be single string "pan,tilt,duration" or separated fields
            if len(row) == 1 and ',' in row[0]:
                parts = [p.strip() for p in row[0].split(',')]
            else:
                parts = [p.strip() for p in row if p.strip() != '']
            if len(parts) < 3:
                continue
            csv_lines.append(','.join(parts[:3]))

# --- 4. Main Loop to Read Data and Plot ---
if CSV_FILE:
    print("Plotting from CSV. The plot window can be closed to stop early.")
else:
    print("Starting to receive data. The plot will update live.")
    print("Will automatically stop when the data stream ends.")

last_data_time = time.time() # Initialize timer to detect when scanning stops

try:
    # If CSV mode, iterate through file lines; otherwise read from serial
    if CSV_FILE:
        for line in csv_lines:
            if not plt.fignum_exists(fig.number):
                break
            # mimic live pacing a little
            time.sleep(0.001)
            if line:
                try:
                    pan_deg_str, tilt_deg_str, duration_str = line.split(',')
                    pan_deg = float(pan_deg_str)
                    tilt_deg = float(tilt_deg_str)
                    duration = float(duration_str)

                    r = get_calibrated_distance_inches(duration)
                    if r <= 0 or r > 30:
                        continue

                    pan_rad = math.radians(pan_deg - 90)
                    tilt_rad = math.radians(tilt_deg)
                    r1 = 2.0
                    r2 = 1.6

                    x_ee = r1 * math.cos(pan_rad) + r2 * math.cos(tilt_rad) * math.cos(pan_rad)
                    y_ee = r1 * math.sin(pan_rad) + r2 * math.cos(tilt_rad) * math.sin(pan_rad)
                    z_ee = r2 * math.sin(tilt_rad)

                    dir_x = math.cos(tilt_rad) * math.cos(pan_rad)
                    dir_y = math.cos(tilt_rad) * math.sin(pan_rad)
                    dir_z = math.sin(tilt_rad)

                    x = x_ee + r * dir_x
                    y = y_ee + r * dir_y
                    z = z_ee + r * dir_z

                    points.append((x, y, z))

                    if len(points) % 10 == 0:
                        ax.clear()
                        x_coords, y_coords, z_coords = zip(*points)
                        ax.scatter(x_coords, y_coords, z_coords, c=z_coords, cmap='viridis', marker='.')
                        ax.set_xlabel('X (inches)')
                        ax.set_ylabel('Y (inches)')
                        ax.set_zlabel('Z (inches)')
                        ax.set_title('Live 3D Scan (from CSV)')
                        ax.set_xlim([0, 20])
                        ax.set_ylim([-20, 0])
                        ax.set_zlim([-10, 10])
                        plt.pause(0.001)

                except (ValueError, IndexError):
                    print(f"Warning: Could not parse CSV line: '{line}'")
        # finished reading CSV
    else:
        while plt.fignum_exists(fig.number): # Loop as long as the plot window is open
            line = ser.readline().decode('utf-8').strip()
            print(line)
            if line:
                last_data_time = time.time() # Reset timer because we received data
                try:
                    # Split the "pan,tilt,duration" string
                    pan_deg_str, tilt_deg_str, duration_str = line.split(',')
                    
                    pan_deg = float(pan_deg_str)
                    tilt_deg = float(tilt_deg_str)
                    duration = float(duration_str)

                    # Convert duration to a real distance using our function
                    r = get_calibrated_distance_inches(duration)
                    print(r)
                    # Ignore invalid sensor readings (too far or no echo)
                    if r <= 0 or r > 30: # Filter out points that are 0 or too far away (e.g., >30 inches)
                        continue
                    # --- Spherical to Cartesian Coordinate Conversion ---
                    pan_rad = math.radians(pan_deg - 90)
                    tilt_rad = math.radians(tilt_deg)
                    r1 = 2.0   # base-to-tilt pivot
                    r2 = 1.6   # tilt link length

                    # --- Compute end effector (sensor) position ---
                    x_ee = r1 * math.cos(pan_rad) + r2 * math.cos(tilt_rad) * math.cos(pan_rad)
                    y_ee = r1 * math.sin(pan_rad) + r2 * math.cos(tilt_rad) * math.sin(pan_rad)
                    z_ee = r2 * math.sin(tilt_rad)

                    # --- Unit vector in sensor pointing direction ---
                    dir_x = math.cos(tilt_rad) * math.cos(pan_rad)
                    dir_y = math.cos(tilt_rad) * math.sin(pan_rad)
                    dir_z = math.sin(tilt_rad)

                    # --- Compute object position ---
                    x = x_ee + r * dir_x
                    y = y_ee + r * dir_y
                    z = z_ee + r * dir_z

                    print(f"Object position: x={x:.2f}, y={y:.2f}, z={z:.2f}")
                    points.append((x, y, z))

                    # --- Live Plot Update ---
                    if len(points) % 10 == 0:
                        ax.clear()
                        x_coords, y_coords, z_coords = zip(*points)
                        ax.scatter(x_coords, y_coords, z_coords, c=z_coords, cmap='viridis', marker='.')
                        
                        ax.set_xlabel('X (inches)')
                        ax.set_ylabel('Y (inches)')
                        ax.set_zlabel('Z (inches)')
                        ax.set_title('Live 3D Scan Visualization')
                        ax.set_xlim([0, 20])
                        ax.set_ylim([-20, 0])
                        ax.set_zlim([-10, 10])
                        plt.pause(0.001)

                except (ValueError, IndexError):
                    print(f"Warning: Could not parse line: '{line}'")
            
            # If no data has been received for 10 seconds, assume the scan is done
            if time.time() - last_data_time > 10.0:
                print("\nNo data received for 10 seconds. Assuming scan is complete.")
                break # Exit the loop to finalize and save the plot

except KeyboardInterrupt:
    print("\nProgram stopped by user.")

finally:
    # --- Final Plot and Save ---
    if points:
        print("Generating final plot...")
        plt.ioff() # Turn off interactive mode for the final static plot
        ax.clear()
        x_coords, y_coords, z_coords = zip(*points)
        ax.scatter(x_coords, y_coords, z_coords, c=z_coords, cmap='viridis', marker='.')
        ax.set_xlabel('X (inches)')
        ax.set_ylabel('Y (inches)')
        ax.set_zlabel('Z (inches)')
        ax.set_title('Final 3D Scan')
        ax.set_xlim([0, 20])
        ax.set_ylim([-20, 0])
        ax.set_zlim([-10, 10])        
        # Create a unique filename with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"3d_scan_hi{timestamp}.png"
        
        try:
            # Save the figure to a file with high resolution
            plt.savefig(filename, dpi=300)
            print(f"Successfully saved plot to {filename}")
        except Exception as e:
            print(f"Error: Could not save the plot. {e}")

        # Show the plot window until the user closes it
        print("Displaying final plot. Close the window to exit.")
        plt.show()

    if ser:
        ser.close()
        print("Serial port closed.")

