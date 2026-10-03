import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_kinematic_residual(df):
    dt = 0.02
    gnss_accel_n = np.gradient(df['gnss_vel_n'], dt)
    gnss_accel_e = np.gradient(df['gnss_vel_e'], dt)
    gnss_accel_mag = np.sqrt(gnss_accel_n**2 + gnss_accel_e**2)
    gnss_accel_mag = pd.Series(gnss_accel_mag).rolling(window=10, min_periods=1).mean().values

    imu_accel_mag = np.sqrt(df['imu_accel_x']**2 + df['imu_accel_y']**2)
    residual = np.abs(gnss_accel_mag - imu_accel_mag)
    mu_w = pd.Series(residual).rolling(window=25, min_periods=1).mean().values
    
    return residual, mu_w

def run_diagnostic():
    project_root = os.path.expanduser("~/Documents/Drone_GPS_Simulation")
    synced_dir = os.path.join(project_root, "data", "processed", "synced")

    # 1. Get nominal baseline stats
    nominal_path = os.path.join(synced_dir, "nominal")
    nom_res = []
    for f in os.listdir(nominal_path):
        if f.endswith(".csv"):
            _, mu_w = calculate_kinematic_residual(pd.read_csv(os.path.join(nominal_path, f)))
            nom_res.extend(mu_w)
    
    mu_nom = np.mean(nom_res)
    sigma_nom = np.std(nom_res)
    mah_thresh = mu_nom + (3.0 * sigma_nom)

    # 2. Load one Stealth Attack flight
    stealth_path = os.path.join(synced_dir, "stealth_attack", "flight_01.csv") # Change if flight_01 is missing
    if not os.path.exists(stealth_path):
        stealth_path = os.path.join(synced_dir, "stealth_attack", os.listdir(os.path.join(synced_dir, "stealth_attack"))[0])
    
    df = pd.read_csv(stealth_path)
    residual, mu_w = calculate_kinematic_residual(df)
    
    # 3. Calculate metrics
    z_scores = (mu_w - mu_nom) / sigma_nom
    
    # CUSUM Math
    LAMBDA = 0.85
    BETA = 0.5
    cusum_vals = np.zeros(len(df))
    S = 0.0
    for i in range(len(df)):
        S = max(0, S * LAMBDA + (z_scores[i] - BETA))
        cusum_vals[i] = S

    # --- Plotting ---
    t = df['time_sec']
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Internal Detector State: Stealth Attack (Injected at t=25s)", fontsize=16)

    # Plot 1: Raw Residuals
    axes[0].plot(t, residual, label="Raw Kinematic Residual", color="gray", alpha=0.5)
    axes[0].plot(t, mu_w, label="Rolling Mean (mu_w)", color="blue", linewidth=2)
    axes[0].axvline(25.0, color='red', linestyle='--', label="Attack Start")
    axes[0].set_ylabel("Accel Mismatch (m/s^2)")
    axes[0].set_ylim(0, 20)
    axes[0].legend()
    axes[0].grid(True)

    # Plot 2: Mahalanobis Z-Score
    axes[1].plot(t, z_scores, label="Z-Score (Mahalanobis)", color="orange")
    axes[1].axhline(3.0, color='red', linestyle='-', label="Detection Threshold (3 Sigma)")
    axes[1].axvline(25.0, color='red', linestyle='--')
    axes[1].set_ylabel("Standard Deviations")
    axes[1].set_ylim(0, 20)
    axes[1].legend()
    axes[1].grid(True)

    # Plot 3: Leaky CUSUM Accumulator
    axes[2].plot(t, cusum_vals, label="Leaky CUSUM Accumulator (S_k)", color="purple", linewidth=2)
    axes[2].axvline(25.0, color='red', linestyle='--')
    axes[2].set_ylabel("CUSUM Score")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].set_ylim(0, 20)
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_diagnostic()