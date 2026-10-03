import os
import pandas as pd

def sync_flight_data(flight_dir, out_filepath):
    # Define the 5 expected files from the extraction step
    csv_files = {
        'imu': os.path.join(flight_dir, 'imu.csv'),
        'gnss': os.path.join(flight_dir, 'gnss.csv'),
        'ekf': os.path.join(flight_dir, 'ekf_estimated.csv'),
        'innov': os.path.join(flight_dir, 'ekf_innovations.csv'),
        'gt': os.path.join(flight_dir, 'ground_truth.csv')
    }

    dataframes = []
    for name, path in csv_files.items():
        if not os.path.exists(path):
            print(f"[-] Missing {name}.csv in {flight_dir}, skipping flight...")
            return False
        
        df = pd.read_csv(path)
        
        # Convert microsecond timestamps to Pandas Datetime objects for time-aware resampling
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='us')
        df.set_index('datetime', inplace=True)
        
        # Drop any duplicate timestamps (can happen occasionally in SITL logging)
        df = df[~df.index.duplicated(keep='first')] 
        
        # Prefix columns (e.g., 'x' becomes 'ekf_x') so they don't overwrite each other
        df.columns = [f"{name}_{col}" if col != 'timestamp' else col for col in df.columns]
        dataframes.append(df)

    # 1. Merge all sensor dataframes into one massive timeline
    combined = pd.concat(dataframes, axis=1)
    combined.sort_index(inplace=True)

    # 2. Resample everything to exactly 50Hz (20ms intervals)
    # .mean() averages the high-rate IMU samples inside each 20ms window
    # .interpolate() draws a straight line between the 10Hz GPS samples
    print("    - Resampling and interpolating to 50Hz...")
    synced = combined.resample('20ms').mean().interpolate(method='linear')
    
    # Drop rows at the very start/end where some sensors hadn't booted up yet
    synced.dropna(inplace=True)

    # 3. Create a clean 'time_sec' column starting at 0.0 seconds for easy math
    synced['time_sec'] = (synced.index - synced.index[0]).total_seconds()
    
    # 4. Save the synchronized flat file
    synced.to_csv(out_filepath, index=False)
    return True

def main():
    project_root = os.path.expanduser("~/Documents/Drone_GPS_Simulation")
    processed_dir = os.path.join(project_root, "data", "processed")
    synced_dir = os.path.join(processed_dir, "synced")
    
    categories = ["nominal", "step_attack", "ramp_attack", "stealth_attack"]
    
    for cat in categories:
        cat_dir = os.path.join(processed_dir, cat)
        out_cat_dir = os.path.join(synced_dir, cat)
        os.makedirs(out_cat_dir, exist_ok=True)
        
        if not os.path.exists(cat_dir):
            continue
            
        # Find all flight_XX folders inside the category
        flight_dirs = sorted([d for d in os.listdir(cat_dir) if os.path.isdir(os.path.join(cat_dir, d))])
        
        for flight in flight_dirs:
            flight_path = os.path.join(cat_dir, flight)
            out_file = os.path.join(out_cat_dir, f"{flight}.csv")
            
            print(f"[*] Synchronizing: {cat}/{flight} -> synced/{cat}/{flight}.csv")
            success = sync_flight_data(flight_path, out_file)
            if success:
                print(f"    [+] Success")

if __name__ == "__main__":
    main()