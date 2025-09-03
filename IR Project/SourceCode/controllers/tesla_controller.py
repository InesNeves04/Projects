import math
from vehicle import Driver
from controller import Camera, Lidar
import numpy as np
import cv2
import os
import csv

lane_errors = []
heading_errors = []
collision_events = 0
oscillation_count = 0
last_steering_angle = 0

def save_metrics():
    elapsed_time = driver.getTime() - simulation_start_time
    last_lane_error = lane_errors[-1] if lane_errors else 0
    last_variance_error = np.var(lane_errors) if lane_errors else 0
    last_heading_error = heading_errors[-1] if heading_errors else 0
    total_oscillations = oscillation_count

    file_exists = os.path.isfile('performance_metrics.csv')

    with open('performance_metrics.csv', mode='a', newline='') as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(['Elapsed Time (s)', 'Lane Error', 'Error Variance', 'Heading Error', 'Oscillations', 'Collisions'])

        writer.writerow([round(elapsed_time, 2),
            last_lane_error,
            last_variance_error,
            last_heading_error,
            total_oscillations,
            collision_events
        ])


# === PID Controller ===
class PIDController:
    def __init__(self, Kp, Ki, Kd, setpoint):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.previous_error = 0
        self.integral = 0

    def compute(self, process_variable, dt):
        error = self.setpoint - process_variable
        P_out = self.Kp * error
        self.integral += error * dt
        I_out = self.Ki * self.integral
        derivative = (error - self.previous_error) / dt
        D_out = self.Kd * derivative
        output = P_out + I_out + D_out
        self.previous_error = error
        return output


# === Driver, Camera and LIDAR Activation ===
driver = Driver()
driver.setDippedBeams(True)
driver.setCruisingSpeed(20.0)
BasicTimeStep = int(driver.getBasicTimeStep())

# Camera Setup
camera = Camera("camera")
camera.enable(BasicTimeStep)
width = camera.getWidth()
height = camera.getHeight()

# LIDAR Setup
lidar = Lidar("lidar")
lidar.enable(BasicTimeStep)
lidar.enablePointCloud()

# === Initialize PID controller ===
pid = PIDController(Kp=0.04, Ki=0.001, Kd=0.01, setpoint=0)

# Saves the images
os.makedirs("frames", exist_ok=True)
frame_counter = 0

def process_image(raw_image):
    global frame_counter
    image = np.frombuffer(raw_image, np.uint8).reshape((height, width, 4))

    # === Convert and save original frame ===
    image_bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    cv2.imwrite(f"frames/frame_{frame_counter:04d}_bgr.png", image_bgr)

    # === Convert to HSV and save ===
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    cv2.imwrite(f"frames/frame_{frame_counter:04d}_hsv.png", hsv)

    # === Threshold yellow mask ===
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    mask_r = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # === Apply ROI (lower part of the image) ===
    mask = np.zeros_like(mask_r)
    mask[int(height * 0.7):, :] = mask_r[ int(height * 0.7):, :]

    # === Edge detection and save ===
    edges = cv2.Canny(mask, 100, 200)
    cv2.imwrite(f"frames/frame_{frame_counter:04d}_canny.png", edges)

    # === Hough Line Detection ===
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=30, maxLineGap=10)
    image_lines = image_bgr.copy()
    image_selected = image_bgr.copy()

    # === Colors for visualization ===
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (255, 127, 0), (127, 0, 255),
    ]

    best_line = None
    max_length = 0

    if lines is not None:
        for idx, line in enumerate(lines):
            x1, y1, x2, y2 = line[0]

            # Draw all lines
            color = colors[idx % len(colors)]
            cv2.line(image_lines, (x1, y1), (x2, y2), color, 2)

            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > max_length:
                max_length = length
                best_line = (x1, y1, x2, y2)

        # Save image with all lines
        cv2.imwrite(f"frames/frame_{frame_counter:04d}_hough_colored.png", image_lines)

        # === Direction error based in the best angle and the center of the line ===
        if best_line is not None:

            x1, y1, x2, y2 = best_line
            cv2.line(image_selected, (x1, y1), (x2, y2), (0, 255, 255), 3)
            cv2.imwrite(f"frames/frame_{frame_counter:04d}_selected_line.png", image_selected)

            dx = x2 - x1
            dy = y2 - y1
            angle = math.atan2(dy, dx)
            desired_angle = -math.pi / 2  # Vertical Line
            angle_error = angle - desired_angle

            # Normalize the angle_error between -pi and pi
            angle_error = (angle_error + math.pi) % (2 * math.pi) - math.pi

            # Adjust the angle_error depending on the transition
            if abs(angle_error) > 0.5:
                angle_error *= 0.5  # Reduce the impact of the error in steep curves

            # Mid Point of the Line
            mid_x = (x1 + x2) // 2
            center_error = (mid_x - (width // 2)) / (width // 2)  # Relative error in relation to the center of the image

            # If the steering error is large, reduce the impact from the center of the line
            if abs(angle_error) > 0.1:  # If the line is too steep, reduce the impact of the center
                center_error *= 0.5
            else:
                center_error *= 1.0  # If the line is almost straight, prioritize the center

            # Combining errors to adjust direction
            error = angle_error + 0.001 * center_error  # Adjustable weight for center error

            heading_errors.append(error)

            frame_counter += 1
            return error

    # === Fallback: moments if no lines detected ===
    moments = cv2.moments(mask)
    if moments["m00"] > 0:
        cx = int(moments["m10"] / moments["m00"])
        error = cx - (width // 2)

        # If no line is detected, continue straight
        if abs(error) < 10:  # Tolerance for small variations
            error = 0.0

        frame_counter += 1
        return error

    frame_counter += 1
    return None


def smooth_steering_update(current, target):
    delta = target - current
    if abs(delta) > max_steering_change:
        delta = max_steering_change if delta > 0 else -max_steering_change
    return current + delta


save_interval = 0.5
last_save_time = driver.getTime()

last_time = driver.getTime()
base_speed = 20.0  # Base speed
min_speed = 10.0
speed = base_speed

# State variables of the contouring maneuver
initial_speed = base_speed
avoidance_started_time = None
avoidance_steering_angle = 0.0
current_steering_angle = 0.0
avoidance_duration = 0.0
in_avoidance = False
returning_to_line = False

max_avoidance_steering = 0.9  # Maximum turning angle for more aggressive contouring
max_steering_change = 0.01  # Maximum increment per step for curve smoothing
min_avoidance_time = 0.5  # Minimum time to hold the maneuver before returning

# Global variable to store contour direction (1 = left, -1 = right)
avoidance_direction = 0
simulation_start_time = driver.getTime()

while driver.step() != -1:
    current_time = driver.getTime()

    dt = current_time - last_time
    last_time = current_time

    ranges = lidar.getRangeImage()
    valid_ranges = [r for r in ranges if r > 0 and not math.isinf(r) and r == r]

    obstacle_detected = False
    threshold = 7.0  # Distance to detect obstacle

    if valid_ranges:
        min_distance = min(valid_ranges)
        if min_distance < threshold:
            obstacle_detected = True

    #1 - Start contour
    if obstacle_detected and not in_avoidance and not returning_to_line:
        print("[INFO] Obstacle detected - starting contour")
        in_avoidance = True
        avoidance_started_time = current_time
        avoidance_duration = 0.0
        initial_speed = speed
        speed = max(min_speed, base_speed * (min_distance / threshold))
        driver.setCruisingSpeed(speed)

        steering_scale = (threshold - min_distance) / threshold
        steering_scale = max(0.4, min(1.0, steering_scale))

        clean_ranges = [r if r > 0 and not math.isinf(r) and r == r else float('inf') for r in ranges]

        mid = len(clean_ranges) // 2
        front_left = min(clean_ranges[:mid])
        front_right = min(clean_ranges[mid:])

        if front_left < front_right:
            avoidance_steering_angle = steering_scale * max_avoidance_steering  # turn left
        else:
            avoidance_steering_angle = -steering_scale * max_avoidance_steering  # turn right

        # Saves the direction of the contour
        avoidance_direction = 1 if avoidance_steering_angle > 0 else -1

        print(f"[DEBUG] Turning {'left' if avoidance_direction == 1 else 'right'} with angle {avoidance_steering_angle:.2f}")
        print(f"")


    # 2 - Still in contour
    if in_avoidance:
        if obstacle_detected:
            current_steering_angle = smooth_steering_update(current_steering_angle, avoidance_steering_angle)
            driver.setSteeringAngle(current_steering_angle)

            speed = max(min_speed, base_speed * (min_distance / threshold))
            driver.setCruisingSpeed(speed)
            print(f"[INFO] Going around... Angle: {current_steering_angle:.2f}, Speed: {speed:.2f}")
        else:
            elapsed_avoidance = current_time - avoidance_started_time
            if elapsed_avoidance > min_avoidance_time:
                print(f"[INFO] Obstacle overcome after {elapsed_avoidance:.2f}s — returning to the line.")
                in_avoidance = False
                returning_to_line = True
                avoidance_duration = elapsed_avoidance
                avoidance_started_time = current_time
            else:
                current_steering_angle = smooth_steering_update(current_steering_angle, avoidance_steering_angle)
                driver.setSteeringAngle(current_steering_angle)
                driver.setCruisingSpeed(min_speed)

    # 3 - Returning to the original line
    if returning_to_line:
        elapsed_return = current_time - avoidance_started_time
        print(f"Elapsed_return: {elapsed_return} --- Avoidance_duration:{avoidance_duration}")
        if elapsed_return < avoidance_duration:

            # Here we reverse direction to return to the center
            target_steering_angle = -avoidance_direction * max_avoidance_steering
            current_steering_angle = smooth_steering_update(current_steering_angle, target_steering_angle)
            driver.setSteeringAngle(current_steering_angle)
            driver.setCruisingSpeed(initial_speed)
            print(f"[INFO] Refocusing... Angle: {current_steering_angle:.2f} ({elapsed_return:.2f}s)")
        else:
            driver.setSteeringAngle(0)
            driver.setCruisingSpeed(base_speed)
            returning_to_line = False
            avoidance_steering_angle = 0.0
            current_steering_angle = 0.0
            avoidance_direction = 0
            print("[INFO] Correction completed. Back to normal driving.")


    # === Lane tracking ===
    if not in_avoidance and not returning_to_line:
        raw_image = camera.getImage()
        if raw_image:
            error = process_image(raw_image)
            if error is not None:
                lane_errors.append(abs(error))
                steering_angle = -pid.compute(error, dt)
                steering_angle = max(-1, min(1, steering_angle))
                driver.setSteeringAngle(steering_angle)

                if last_steering_angle * steering_angle < 0:
                    oscillation_count += 1
                last_steering_angle = steering_angle


                speed = max(min_speed, base_speed - abs(error) * 0.5)
                driver.setCruisingSpeed(speed)
            else:
                speed = base_speed
                driver.setSteeringAngle(0)
                driver.setCruisingSpeed(speed)
        else:
            speed = base_speed
            driver.setCruisingSpeed(speed)

    # Save metrics at each defined interval
    if current_time - last_save_time > save_interval:
        save_metrics()
        last_save_time = current_time