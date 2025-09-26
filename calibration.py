import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import io

# --- 1. Load Your Calibration Data ---
# Create a string that acts like a file to load the data
calibration_data_string = """Actual_inch,measured_duration
1,211
2,305
3,443
4,585
5,718
6,865
7,1010
8,1157
9,1302
10,1452
11,1618
12,1760
13,1890
14,2033
15,2150
16,2300
17,2470
18,2630
19,2780
20,2930
"""

# Use pandas to read the string data
df_calibration = pd.read_csv(io.StringIO(calibration_data_string))

# Extract the data columns
# The sensor reading ('measured_duration') is our independent variable (X)
measured_duration = df_calibration["measured_duration"].values.reshape(-1, 1)
# The actual distance is our dependent variable (y)
actual_inch = df_calibration["Actual_inch"].values

# --- 2. Create the Calibration Function ---
# Fit a linear regression model to predict actual distance from the sensor reading
model = LinearRegression()
model.fit(measured_duration, actual_inch)

# Get the slope and intercept from the trained model
slope = model.coef_[0]
intercept = model.intercept_

print("--- Calibration Function ---")
print(f"Slope: {slope:.4f} inches/unit")
print(f"Intercept: {intercept:.4f} inches")
print(f"Formula: Predicted_Distance_inch = {slope:.4f} * measured_duration + {intercept:.4f}\n")


# --- 3. Generate the Calibration Plot ---
# Predict the distances using the model for plotting the trendline
predicted_inch_line = model.predict(measured_duration)

plt.figure(figsize=(10, 6))
plt.scatter(measured_duration, actual_inch, label="Actual Data Points", color="blue")
plt.plot(measured_duration, predicted_inch_line, label="Linear Regression Fit", color="red")
plt.title("Sensor Calibration Plot")
plt.xlabel("Raw Sensor Reading (measured_duration)")
plt.ylabel("Actual Distance (inches)")
plt.legend()
plt.grid(True)
print("Displaying Calibration Plot...")
plt.show()


# --- 4. Load Validation Data for Error Plot ---
validation_data_string = """Actual_inch,measured_duration
1.5,257
3.5,524
5.5,790
6.5,955
"""
df_validation = pd.read_csv(io.StringIO(validation_data_string))

# Extract the validation data
validation_actual_inch = df_validation["Actual_inch"].values
validation_measured_duration = df_validation["measured_duration"].values.reshape(-1, 1)

# --- 5. Predict Distances for the Validation Data ---
# Use the *original* model to predict distances for this new data
validation_predicted_inch = model.predict(validation_measured_duration)

print("\n--- Error Analysis ---")
for i in range(len(validation_actual_inch)):
    print(f"Actual: {validation_actual_inch[i]:.1f} in, Sensor Reading: {validation_measured_duration[i][0]}, Predicted: {validation_predicted_inch[i]:.2f} in")


# --- 6. Generate the Error Plot ---
plt.figure(figsize=(8, 8))
# Plot predicted vs. actual distances
plt.scatter(validation_actual_inch, validation_predicted_inch, label="Validation Points", color="green", s=100)

# Create an "ideal" line where predicted equals actual (y=x)
# Find the min/max to create a perfectly diagonal line across the plot
min_val = min(validation_actual_inch.min(), validation_predicted_inch.min()) - 0.5
max_val = max(validation_actual_inch.max(), validation_predicted_inch.max()) + 0.5
ideal_line = np.linspace(min_val, max_val, 100)

plt.plot(ideal_line, ideal_line, 'r--', label="Ideal Prediction (y=x)")

plt.title("Error Plot: Predicted vs. Actual Distance")
plt.xlabel("Actual Distance (inches)")
plt.ylabel("Predicted Distance (inches)")
plt.axis('equal') # This ensures the x and y axes have the same scale, making the ideal line a true 45-degree diagonal
plt.grid(True)
plt.legend()
print("\nDisplaying Error Plot...")
plt.show()
