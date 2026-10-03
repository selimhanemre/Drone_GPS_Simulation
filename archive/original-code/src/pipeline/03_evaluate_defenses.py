import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score
import warnings
warnings.filterwarnings('ignore')

# Global Plotting Configuration for IEEE/ACM Paper Readability
plt.rcParams.update({
    'font.size': 14,
    'axes.titlesize': 18,
    'axes.labelsize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'legend.fontsize': 14,
    'lines.linewidth': 2.5
})

# ---------------------------------------------------------
# 1. Core Mathematical Functions
# ---------------------------------------------------------
def calculate_kinematic_residual(df):
    dt = 0.02 # 50Hz
    gnss_accel_n = np.gradient(df['gnss_vel_n'], dt)
    gnss_accel_e = np.gradient(df['gnss_vel_e'], dt)
    gnss_accel_mag = np.sqrt(gnss_accel_n**2 + gnss_accel_e**2)
    gnss_accel_mag = pd.Series(gnss_accel_mag).rolling(window=10, min_periods=1).mean().values

    imu_accel_mag = np.sqrt(df['imu_accel_x']**2 + df['imu_accel_y']**2)
    residual = np.abs(gnss_accel_mag - imu_accel_mag)
    mu_w = pd.Series(residual).rolling(window=25, min_periods=1).mean().values
    
    return residual, mu_w

def apply_crash_truncation(df):
    return df[df['time_sec'] <= 50.0].reset_index(drop=True)

# ---------------------------------------------------------
# 2. Main Evaluation Pipeline
# ---------------------------------------------------------
def run_evaluation():
    project_root = os.path.expanduser("~/Documents/Drone_GPS_Simulation")
    synced_dir = os.path.join(project_root, "data", "processed", "synced")
    metrics_dir = os.path.join(project_root, "results", "metrics")
    figs_dir = os.path.join(project_root, "results", "figures")
    os.makedirs(metrics_dir, exist_ok=True)
    os.makedirs(figs_dir, exist_ok=True)

    print("[*] Training Baselines on Nominal Flights...")
    nominal_residuals = []
    
    nominal_path = os.path.join(synced_dir, "nominal")
    for file in os.listdir(nominal_path):
        if file.endswith(".csv"):
            df = apply_crash_truncation(pd.read_csv(os.path.join(nominal_path, file)))
            _, mu_w = calculate_kinematic_residual(df)
            nominal_residuals.extend(mu_w)
            
    nominal_residuals = np.array(nominal_residuals).reshape(-1, 1)
    mu_nom = np.mean(nominal_residuals)
    sigma_nom = np.std(nominal_residuals)
    mah_threshold = mu_nom + (3.0 * sigma_nom)
    
    iso_forest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    iso_forest.fit(nominal_residuals)

    print("[*] Evaluating Defenses Across All 40 Flights...")
    results = []
    comparison_data = {}
    
    LAMBDA = 0.85
    BETA = 0.5
    CUSUM_THRESHOLD = 10.0
    ATTACK_START_TIME = 20.0

    categories = ["nominal", "step_attack", "ramp_attack", "stealth_attack"]
    first_stealth_plotted = False
    
    for cat in categories:
        cat_dir = os.path.join(synced_dir, cat)
        if not os.path.exists(cat_dir): continue
            
        for file in sorted(os.listdir(cat_dir)):
            if not file.endswith(".csv"): continue
                
            flight_id = file.replace(".csv", "")
            df = apply_crash_truncation(pd.read_csv(os.path.join(cat_dir, file)))
            residual, mu_w = calculate_kinematic_residual(df)
            
            y_true = np.zeros(len(df))
            if cat != "nominal":
                y_true[df['time_sec'] >= ATTACK_START_TIME] = 1
                    
            z_scores = (mu_w - mu_nom) / sigma_nom
            y_pred_mah = (mu_w > mah_threshold).astype(int)
            
            y_pred_iso = iso_forest.predict(mu_w.reshape(-1, 1))
            y_pred_iso = (y_pred_iso == -1).astype(int)
            
            y_pred_cusum = np.zeros(len(df))
            cusum_vals = np.zeros(len(df))
            S = 0.0
            for i in range(len(df)):
                S = max(0, S * LAMBDA + (z_scores[i] - BETA))
                cusum_vals[i] = S
                if S > CUSUM_THRESHOLD:
                    y_pred_cusum[i] = 1

            if flight_id == "flight_01" or (cat not in comparison_data):
                comparison_data[cat] = {
                    't': df['time_sec'], 
                    'cusum': cusum_vals,
                    'ekf_y': df['ekf_y'],
                    'gt_y_true': df['gt_y_true']
                }

            # Alarm Latching
            if np.any(y_pred_mah == 1): y_pred_mah[np.argmax(y_pred_mah == 1):] = 1
            if np.any(y_pred_iso == 1): y_pred_iso[np.argmax(y_pred_iso == 1):] = 1
            if np.any(y_pred_cusum == 1): y_pred_cusum[np.argmax(y_pred_cusum == 1):] = 1

            # Metrics
            for model_name, y_pred in [("Mahalanobis", y_pred_mah), ("IsoForest", y_pred_iso), ("Leaky_CUSUM", y_pred_cusum)]:
                f1 = f1_score(y_true, y_pred, zero_division=0)
                
                fp_mask = (y_true == 0) & (y_pred == 1)
                false_positive = 1 if fp_mask.any() else 0
                
                latency = None
                if cat != "nominal":
                    true_positives = np.where((y_true == 1) & (y_pred == 1))[0]
                    if len(true_positives) > 0 and not false_positive:
                        detect_time = df.loc[true_positives[0], 'time_sec']
                        latency = max(0, detect_time - ATTACK_START_TIME)
                
                results.append({
                    "Flight": f"{cat}/{flight_id}",
                    "Category": cat, "Detector": model_name,
                    "F1_Score": round(f1, 3), 
                    "Latency_sec": latency,
                    "False_Positive": false_positive
                })

            if cat == "stealth_attack" and not first_stealth_plotted:
                plot_stealth_internals(df['time_sec'], residual, mu_w, z_scores, cusum_vals, figs_dir)
                first_stealth_plotted = True

    results_df = pd.DataFrame(results)
    results_df.to_csv(os.path.join(metrics_dir, "detector_benchmark.csv"), index=False)
    
    print("\n[+] Benchmark Complete! Performance Summary:")
    summary = results_df.groupby(["Category", "Detector"]).agg({
        "F1_Score": "mean",
        "Latency_sec": "mean",
        "False_Positive": "sum"
    }).round(3)
    summary.rename(columns={"False_Positive": "Total False Positives"}, inplace=True)
    print(summary)
    
    plot_attack_comparison(comparison_data, figs_dir)
    plot_physical_deviation(comparison_data, figs_dir)
    
    print(f"\n[+] Saved metrics to: {metrics_dir}")
    print(f"[+] Saved figures to: {figs_dir}")

# ---------------------------------------------------------
# 3. Figure Generation Functions
# ---------------------------------------------------------
def plot_stealth_internals(t, residual, mu_w, z_scores, cusum_vals, out_dir):
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Internal State: Stealth Evasion vs. CUSUM", fontweight='bold', fontsize=20)

    axes[0].plot(t, residual, label="Raw Kinematic Residual", color="gray", alpha=0.5)
    axes[0].plot(t, mu_w, label=r"Rolling Mean ($r_{kin}$)", color="blue")
    axes[0].axvline(25.0, color='red', linestyle='--', label="Attack Start")
    axes[0].set_ylabel(r"Mismatch ($m/s^2$)")
    axes[0].legend(loc="upper left")
    axes[0].grid(True)

    axes[1].plot(t, z_scores, label="Z-Score (Mahalanobis)", color="orange")
    axes[1].axhline(3.0, color='red', linestyle='-', label=r"Threshold ($3\sigma$)")
    axes[1].axvline(25.0, color='red', linestyle='--')
    axes[1].set_ylabel("Standard Deviations")
    axes[1].set_ylim(0, max(6, np.max(z_scores)*1.2))
    axes[1].legend(loc="upper left")
    axes[1].grid(True)

    axes[2].plot(t, cusum_vals, label=r"CUSUM Accumulator ($S_k$)", color="purple")
    axes[2].axhline(10.0, color='red', linestyle='-', label="Detection Threshold")
    axes[2].axvline(25.0, color='red', linestyle='--')
    axes[2].set_ylabel("CUSUM Score")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].legend(loc="upper left")
    axes[2].grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "fig_stealth_internals.pdf"), dpi=300, bbox_inches='tight')
    plt.close()

def plot_attack_comparison(comparison_data, out_dir):
    plt.figure(figsize=(12, 7))
    colors = {'nominal': 'green', 'step_attack': 'red', 'ramp_attack': 'orange', 'stealth_attack': 'purple'}
    labels = {'nominal': 'Nominal', 'step_attack': 'Step (5m/s)', 'ramp_attack': r'Ramp (0.25$m/s^2$)', 'stealth_attack': r'Stealth (0.05$m/s^2$)'}

    for cat, data in comparison_data.items():
        plt.plot(data['t'], data['cusum'], label=labels.get(cat, cat), color=colors.get(cat, 'blue'))

    plt.axhline(10.0, color='black', linestyle='--', label="CUSUM Threshold (Alarm Trip)")
    plt.axvline(25.0, color='gray', linestyle=':', label="Spoofing Injected")

    plt.title('Leaky CUSUM Response Across Attack Profiles', fontweight='bold', fontsize=20)
    plt.xlabel('Time (seconds)')
    plt.ylabel(r'CUSUM Score ($S_k$)')
    plt.ylim(-1, 30)
    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "fig_cusum_comparison.pdf"), dpi=300, bbox_inches='tight')
    plt.close()

def plot_physical_deviation(comparison_data, out_dir):
    plt.figure(figsize=(12, 7))
    colors = {'nominal': 'green', 'step_attack': 'red', 'ramp_attack': 'orange', 'stealth_attack': 'purple'}
    labels = {'nominal': 'Nominal', 'step_attack': 'Step Attack', 'ramp_attack': 'Ramp Attack', 'stealth_attack': 'Stealth Attack'}

    for cat, data in comparison_data.items():
        physical_error = np.abs(data['ekf_y'] - data['gt_y_true'])
        plt.plot(data['t'], physical_error, label=labels.get(cat, cat), color=colors.get(cat, 'blue'))

    plt.axvline(25.0, color='gray', linestyle=':', label="Spoofing Injected")
    plt.title('Physical Trajectory Divergence Caused by Spoofing', fontweight='bold', fontsize=20)
    plt.xlabel('Time (seconds)')
    plt.ylabel('East Position Error (meters)')
    plt.legend(loc='upper left')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "fig_physical_deviation.pdf"), dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    run_evaluation()