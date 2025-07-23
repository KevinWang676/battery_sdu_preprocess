# Licensed under the MIT License.
# Copyright (c) Microsoft Corporation.

import os
import numpy as np
import pandas as pd

from tqdm import tqdm
from numba import njit
from typing import List
from pathlib import Path
from scipy.signal import medfilt

from batteryml import BatteryData, CycleData
from batteryml.builders import PREPROCESSORS
from batteryml.preprocess.base import BasePreprocessor


@PREPROCESSORS.register()
class SDUPreprocessor(BasePreprocessor):
    def process(self, parentdir, **kwargs) -> List[BatteryData]:
        path = Path(parentdir)
        raw_files = [Path(f) for f in path.glob('*.csv')]
        
        if not raw_files:
            print("No CSV files found in the directory")
            return 0, 0
        
        if not self.silent:
            print(f"Found {len(raw_files)} CSV files to process")

        process_batteries_num = 0
        skip_batteries_num = 0
        
        # Process each CSV file
        for csv_file in tqdm(raw_files, desc="Processing CSV files"):
            if not self.silent:
                print(f'Processing {csv_file.name}')
            
            # Load the CSV file
            try:
                df = pd.read_csv(csv_file)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
                continue
            
            # Group by Battery_ID to handle multiple batteries in one file
            for battery_id, battery_df in df.groupby('Battery_ID'):
                cell_name = f"Battery_{battery_id}"
                
                # Check whether to skip the processed file
                whether_to_skip = self.check_processed_file(f'CSV_{cell_name}')
                if whether_to_skip == True:
                    skip_batteries_num += 1
                    continue
                
                if not self.silent:
                    print(f'Processing battery {cell_name}')
                
                # Prepare data in the same format as CALCE
                # Since we don't have dates, we'll use a dummy date
                battery_df = battery_df.copy()
                battery_df['date'] = '2023-01-01'  # Dummy date for consistency
                
                # Sort by Test_Time(s) - equivalent to CALCE's date+time sorting
                battery_df = battery_df.sort_values(['Test_Time(s)'])
                
                # Organize cycle index using the same function as CALCE
                battery_df['Cycle_Index'] = organize_cycle_index(battery_df['Cycle_Index'].values)
                
                # Extract required columns
                columns_to_keep = [
                    'date', 'Cycle_Index', 'Test_Time(s)', 'Current(A)', 'Voltage(V)'
                ]
                processed_df = battery_df[columns_to_keep]
                
                clean_cycles, cycles = [], []
                for cycle_index, (_, cycle_df) in enumerate(processed_df.groupby(['date', 'Cycle_Index'])):
                    I = cycle_df['Current(A)'].values  # noqa
                    t = cycle_df['Test_Time(s)'].values
                    V = cycle_df['Voltage(V)'].values
                    
                    # Calculate charge and discharge capacities using the same function as CALCE
                    Qd = calc_Q(I, t, is_charge=False)
                    Qc = calc_Q(I, t, is_charge=True)
                    
                    cycles.append(CycleData(
                        cycle_number=cycle_index,
                        voltage_in_V=V.tolist(),
                        current_in_A=I.tolist(),
                        time_in_s=t.tolist(),
                        charge_capacity_in_Ah=Qc.tolist(),
                        discharge_capacity_in_Ah=Qd.tolist()
                    ))
                
                # Clean the cycles using the same logic as CALCE
                Qd = []
                for cycle_data in cycles:
                    if len(cycle_data.discharge_capacity_in_Ah) > 0:
                        Qd.append(max(cycle_data.discharge_capacity_in_Ah))
                    else:
                        Qd.append(0.0)
                
                if len(Qd) == 0:
                    print(f"No valid cycles found for battery {cell_name}")
                    continue
                
                # Apply median filtering for outlier detection
                if len(Qd) >= 21:
                    Qd_med = medfilt(Qd, 21)
                else:
                    Qd_med = medfilt(Qd, min(len(Qd), 5))  # Use smaller window for short sequences
                
                ths = np.median(abs(np.array(Qd) - Qd_med))
                should_keep = abs(np.array(Qd) - Qd_med) < 3 * ths
                
                clean_cycles, index = [], 0
                for i in range(len(cycles)):
                    if should_keep[i] and Qd[i] > 0.1:
                        index += 1
                        cycles[i].cycle_number = index
                        clean_cycles.append(cycles[i])
                
                if len(clean_cycles) == 0:
                    print(f"No clean cycles found for battery {cell_name}")
                    continue
                
                # Estimate nominal capacity from the first few cycles
                initial_capacities = [max(cycle.discharge_capacity_in_Ah) for cycle in clean_cycles[:5]]
                C = np.mean(initial_capacities) if initial_capacities else 1.0
                
                # Set default battery parameters (can be adjusted based on your battery specifications)
                soc_interval = [0, 1]
                
                battery = BatteryData(
                    cell_id=f'CSV_{cell_name}',
                    form_factor='unknown',  # Adjust based on your battery type
                    anode_material='unknown',  # Adjust based on your battery type
                    cathode_material='unknown',  # Adjust based on your battery type
                    cycle_data=clean_cycles,
                    nominal_capacity_in_Ah=C,
                    max_voltage_limit_in_V=4.2,  # Adjust based on your battery specs
                    min_voltage_limit_in_V=2.7,  # Adjust based on your battery specs
                    SOC_interval=soc_interval
                )
                
                self.dump_single_file(battery)
                process_batteries_num += 1
                
                if not self.silent:
                    tqdm.write(f'File: {battery.cell_id} dumped to pkl file')
        
        return process_batteries_num, skip_batteries_num


@njit
def calc_Q(I, t, is_charge):  # noqa
    """
    Calculate charge/discharge capacity - same function as CALCE preprocessor
    """
    Q = np.zeros_like(I)
    for i in range(1, len(I)):
        if is_charge and I[i] > 0:
            Q[i] = Q[i-1] + I[i] * (t[i] - t[i-1]) / 3600
        elif not is_charge and I[i] < 0:
            Q[i] = Q[i-1] - I[i] * (t[i] - t[i-1]) / 3600
        else:
            Q[i] = Q[i-1]
    return Q


@njit
def organize_cycle_index(cycle_index):
    """
    Organize cycle indices - same function as CALCE preprocessor
    """
    current_cycle, prev_value = cycle_index[0], cycle_index[0]
    for i in range(1, len(cycle_index)):
        if cycle_index[i] != prev_value:
            current_cycle += 1
            prev_value = cycle_index[i]
        cycle_index[i] = current_cycle
    return cycle_index 