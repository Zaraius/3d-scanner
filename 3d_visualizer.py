import serial
import matplotlib.pyplot as plt
import math
import time
import datetime
import argparse
import csv
import os


# SWITCHES BETWEEN ACM0 and ACM1
ARDUINO_COM_PORT = "/dev/ttyACM1"
BAUD_RATE = 115200 # Must match the rate in the Arduino code

# optional csv input which allows to copy paste from Serial monitor
parser = argparse.ArgumentParser(description="3D scan visualizer (live serial or CSV)")
parser.add_argument('--csv-file', '-c', help='Path to CSV file containing pan,tilt,duration lines (use instead of live serial)')
args = parser.parse_args()
CSV_FILE = args.csv_file

# converts the raw `duration` value from the sensor into inches using our values from calibration.
def get_calibrated_distance_inches(duration):
    slope = 0.0069
    intercept = -0.0751
    if duration == 0:
        return 0
    return slope * duration + intercept

# Converts servo measurements and durtaion to x y z position
def compute_point_from_measurement(pan_deg, tilt_deg, duration, r1=2.0, r2=1.6):
    """
    Convert pan, tilt (degrees) and sensor duration into (x,y,z) in inches.
    Returns (x,y,z) or None if the reading is invalid / out of range.
    """
    r = get_calibrated_distance_inches(duration)
    if r <= 0 or r > 30:
        return None

    pan_rad = math.radians(pan_deg - 90)
    tilt_rad = math.radians(tilt_deg)
    # getting end effector position
    x_ee = r1 * math.cos(pan_rad) + r2 * math.cos(tilt_rad) * math.cos(pan_rad)
    y_ee = r1 * math.sin(pan_rad) + r2 * math.cos(tilt_rad) * math.sin(pan_rad)
    z_ee = r2 * math.sin(tilt_rad)

    dir_x = math.cos(tilt_rad) * math.cos(pan_rad)
    dir_y = math.cos(tilt_rad) * math.sin(pan_rad)
    dir_z = math.sin(tilt_rad)

    x = x_ee + r * dir_x
    y = y_ee + r * dir_y
    z = z_ee + r * dir_z

    return (x, y, z)


def update_scatter_plot(ax, points, title='3D Scan', xlim=(0, 20), ylim=(-20, 0), zlim=(-10, 10)):
    """
    Clear and redraw the 3D scatter plot using points list [(x,y,z), ...].
    """
    if not points:
        return
    ax.clear()
    x_coords, y_coords, z_coords = zip(*points)
    ax.scatter(x_coords, y_coords, z_coords, c=z_coords, cmap='viridis', marker='.')
    ax.set_xlabel('X (inches)')
    ax.set_ylabel('Y (inches)')
    ax.set_zlabel('Z (inches)')
    ax.set_title(title)
    ax.set_xlim(list(xlim))
    ax.set_ylim(list(ylim))
    ax.set_zlim(list(zlim))
    plt.pause(0.001)

# Connect to Arduino Serial
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
plt.ion()
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')

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


last_data_time = time.time()

try:
    # If CSV mode, iterate through file lines; otherwise read from serial
    if CSV_FILE:
        for line in csv_lines:
            if not plt.fignum_exists(fig.number):
                break
            time.sleep(0.001)
            if line:
                try:
                    pan_deg_str, tilt_deg_str, duration_str = line.split(',')
                    pan_deg = float(pan_deg_str)
                    tilt_deg = float(tilt_deg_str)
                    duration = float(duration_str)

                    pt = compute_point_from_measurement(pan_deg, tilt_deg, duration)
                    if pt is None:
                        continue
                    points.append(pt)

                    if len(points) % 10 == 0:
                        update_scatter_plot(ax, points, title='Live 3D Scan (from CSV)')

                except (ValueError, IndexError):
                    print(f"Warning: Could not parse CSV line: '{line}'")
        # finished reading CSV
    else:
        while plt.fignum_exists(fig.number):  # Loop as long as the plot window is open
            line = ser.readline().decode('utf-8').strip()
            print(line)
            if line:
                last_data_time = time.time()  # Reset timer because we received data
                try:
                    # Split the "pan,tilt,duration" string
                    pan_deg_str, tilt_deg_str, duration_str = line.split(',')

                    pan_deg = float(pan_deg_str)
                    tilt_deg = float(tilt_deg_str)
                    duration = float(duration_str)

                    pt = compute_point_from_measurement(pan_deg, tilt_deg, duration)
                    if pt is None:
                        continue
                    x, y, z = pt
                    print(f"Object position: x={x:.2f}, y={y:.2f}, z={z:.2f}")
                    points.append(pt)

                    # --- Live Plot Update ---
                    if len(points) % 10 == 0:
                        update_scatter_plot(ax, points, title='Live 3D Scan Visualization')

                except (ValueError, IndexError):
                    print(f"Warning: Could not parse line: '{line}'")

            # If no data has been received for 10 seconds, assume the scan is done
            if time.time() - last_data_time > 10.0:
                print("\nNo data received for 10 seconds. Assuming scan is complete.")
                break  # Exit the loop to finalize and save the plot

except KeyboardInterrupt:
    print("\nProgram stopped by user.")

finally:
     if points:
         print("Generating final plot...")
         plt.ioff()
         update_scatter_plot(ax, points, title='Final 3D Scan')

         timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
         filename = f"3d_scan{timestamp}.png"
         
         try:
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

