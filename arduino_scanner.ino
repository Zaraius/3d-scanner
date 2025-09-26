#include <Servo.h>

// --- Pin Definitions ---
const int PAN_SERVO_PIN = 5;  // Bottom servo
const int TILT_SERVO_PIN = 6; // Top servo
const int TRIG_PIN = A5;
const int ECHO_PIN = A4;

// --- Servo Objects ---
Servo panServo;  // Changed name to be more descriptive
Servo tiltServo;

// --- Scan Settings ---
// You can adjust these to change the scanning area
const int PAN_START_ANGLE = 5;
const int PAN_END_ANGLE = 50;
const int PAN_STEP = 2; // How far the bottom servo moves each time

const int TILT_START_ANGLE = 45 - 30;
const int TILT_END_ANGLE = 45 + 30;
const int TILT_STEP = 1; // How far the top servo moves. A smaller step gives higher resolution.

void setup() {
  // Use a faster baud rate for quicker data transfer
  Serial.begin(115200);

  // Set up the sensor pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Attach servos to their pins  
  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);

  // Move servos to the starting position
//  panServo.write(PAN_START_ANGLE);
//  tiltServo.write(TILT_START_ANGLE);
  panServo.write(5);
  tiltServo.write(45);
  delay(5000);//Wait a moment for servos to get in position
}

void loop() {
  // This outer loop controls the PAN (bottom) servo
  for (int panPos = PAN_START_ANGLE; panPos <= PAN_END_ANGLE; panPos += PAN_STEP) {
    panServo.write(panPos);
    delay(200); // Longer delay to let the bottom servo settle properly

    // This inner loop sweeps the TILT (top) servo from start to end
    for (int tiltPos = TILT_START_ANGLE; tiltPos <= TILT_END_ANGLE; tiltPos += TILT_STEP) {
      scanAndSendData(panPos, tiltPos);
      delay(100);
    }

    // Move the PAN servo to the next position
    panPos += PAN_STEP;
    if (panPos > PAN_END_ANGLE) break; // Exit if we are done
    panServo.write(panPos);
    delay(200);

    // This inner loop sweeps the TILT servo back again for efficiency (S-pattern scan)
    for (int tiltPos = TILT_END_ANGLE; tiltPos >= TILT_START_ANGLE; tiltPos -= TILT_STEP) {
      scanAndSendData(panPos, tiltPos);
      delay(100);

    }
  }
  panServo.write(5);
  tiltServo.write(45);
  // --- Scan Complete ---
  // The program will stop here after one full scan.
  // You can reset the Arduino to start a new scan.
  while (true);
}

/**
 * @brief Moves the tilt servo, takes a sensor reading, and sends all data.
 * @param currentPan The current angle of the bottom (pan) servo.
 * @param currentTilt The current angle of the top (tilt) servo.
 */
void scanAndSendData(int currentPan, int currentTilt) {
  tiltServo.write(currentTilt);
  delay(30); // A small delay to let the tilt servo settle

  // --- Trigger the HC-SR04 Sensor ---
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Read the pulse duration from the echo pin
  long duration = pulseIn(ECHO_PIN, HIGH);

  // --- Send data over Serial ---
  // Format: "pan_angle,tilt_angle,duration"
  // The Python script will parse this exact format.
  Serial.print(currentPan - 5);
  Serial.print(",");
  Serial.print(currentTilt - 45);
  Serial.print(",");
  Serial.println(duration);
}
