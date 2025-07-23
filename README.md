# CSV Battery Data Preprocessor

This preprocessor script (`process_scripts/preprocess_CSV.py`) processes battery charge/discharge cycle data from CSV files into the same format as the CALCE preprocessor. It follows the exact same preprocessing logic and produces compatible `BatteryData` objects.

## Input Data Format

The preprocessor expects CSV files with the following columns:

| Column Name | Description |
|-------------|-------------|
| Unnamed: 0 | Row index |
| Test_Time(s) | Test time in seconds |
| Step_Time(s) | Step time in seconds |
| Cycle_Index | Cycle number |
| Step_Index | Step number within cycle |
| Current(A) | Current in Amperes |
| Voltage(V) | Voltage in Volts |
| Charge_Capacity(Ah) | Charge capacity in Amp-hours |
| Discharge_Capacity(Ah) | Discharge capacity in Amp-hours |
| Charge_Energy(Wh) | Charge energy in Watt-hours |
| Discharge_Energy(Wh) | Discharge energy in Watt-hours |
| Internal_Resistance(Ohm) | Internal resistance in Ohms |
| Aux_Temperature_1(C) | Temperature in Celsius |
| Battery_ID | Unique battery identifier |
| Protocol_ID | Protocol identifier |

## Key Features

### Exact CALCE Compatibility
- Uses the same `calc_Q()` function for capacity calculations
- Applies identical `organize_cycle_index()` logic
- Implements the same cycle cleaning with median filtering
- Produces identical `BatteryData` and `CycleData` structures

### Processing Steps
1. **File Discovery**: Finds all `*.csv` files in the specified directory
2. **Data Loading**: Loads CSV files and groups by `Battery_ID`
3. **Data Sorting**: Sorts by `Test_Time(s)` (equivalent to CALCE's date+time sorting)
4. **Cycle Organization**: Renumbers cycles consecutively using `organize_cycle_index()`
5. **Capacity Calculation**: Calculates charge/discharge capacities from current and time
6. **Outlier Filtering**: Removes outlier cycles using median filtering (21-point filter)
7. **Data Cleaning**: Keeps only cycles with discharge capacity > 0.1 Ah
8. **Battery Object Creation**: Creates `BatteryData` objects with metadata
9. **Serialization**: Saves processed data as pickle files

### Data Processing Logic

#### Capacity Calculation
```python
# Charge capacity (positive current)
if is_charge and I[i] > 0:
    Q[i] = Q[i-1] + I[i] * (t[i] - t[i-1]) / 3600

# Discharge capacity (negative current)  
elif not is_charge and I[i] < 0:
    Q[i] = Q[i-1] - I[i] * (t[i] - t[i-1]) / 3600
```

#### Outlier Detection
- Applies 21-point median filter to discharge capacities
- Removes cycles where `|Qd - Qd_median| > 3 * median_threshold`
- Keeps only cycles with discharge capacity > 0.1 Ah

## Usage

### Basic Usage
```python
from process_scripts.preprocess_CSV import CSVPreprocessor

# Initialize preprocessor
preprocessor = CSVPreprocessor(
    dump_dir='./processed_data',  # Output directory
    silent=False  # Show progress messages
)

# Process CSV files
processed_count, skipped_count = preprocessor.process(
    parentdir='./data'  # Directory containing CSV files
)

print(f"Processed {processed_count} batteries, skipped {skipped_count}")
```

### Using the Test Script
```bash
python test_csv_preprocessor.py
```

This will process any CSV files in the current directory and save the results to `./processed_data/`.

## Output Format

The preprocessor creates `BatteryData` objects with:

- **Cell ID**: `CSV_Battery_{Battery_ID}` (e.g., "CSV_Battery_43")
- **Cycle Data**: List of `CycleData` objects containing:
  - `voltage_in_V`: Voltage measurements
  - `current_in_A`: Current measurements  
  - `time_in_s`: Time measurements
  - `charge_capacity_in_Ah`: Calculated charge capacity
  - `discharge_capacity_in_Ah`: Calculated discharge capacity
- **Metadata**: Battery specifications (adjustable in the script)

## Configuration

You can adjust the following parameters in the script:

```python
# Battery specifications (adjust based on your battery type)
battery = BatteryData(
    form_factor='unknown',           # e.g., 'cylindrical', 'prismatic', 'pouch'
    anode_material='unknown',        # e.g., 'graphite', 'silicon'
    cathode_material='unknown',      # e.g., 'LiCoO2', 'LFP', 'NMC'
    nominal_capacity_in_Ah=C,        # Auto-calculated from data
    max_voltage_limit_in_V=4.2,      # Adjust for your battery
    min_voltage_limit_in_V=2.7,      # Adjust for your battery
    SOC_interval=[0, 1]              # State of charge range
)
```

## Differences from CALCE Preprocessor

While maintaining identical processing logic, this preprocessor differs in:

1. **Input Format**: Reads CSV files instead of ZIP archives
2. **Data Source**: Uses `Battery_ID` for grouping instead of filename-based dates
3. **Date Handling**: Uses dummy dates since CSV data doesn't include timestamps
4. **Metadata**: Uses generic battery specifications (can be customized)

## Error Handling

The preprocessor includes robust error handling:
- Skips corrupted CSV files with error messages
- Handles empty or invalid data gracefully
- Validates that cycles contain sufficient data
- Uses smaller median filter windows for short cycle sequences

## File Structure

```
├── process_scripts/
│   └── preprocess_CSV.py          # Main preprocessor script
├── test_csv_preprocessor.py       # Test/example script
├── CSV_PREPROCESSOR_README.md     # This documentation
├── 71.csv                         # Example input data (Battery_ID=43)
├── 72.csv                         # Example input data (Battery_ID=44)
└── processed_data/                # Output directory (created automatically)
    ├── CSV_Battery_43.pkl         # Processed battery 43 data
    └── CSV_Battery_44.pkl         # Processed battery 44 data
```

## Integration with BatteryML

This preprocessor is fully compatible with the BatteryML framework:
- Registers with `@PREPROCESSORS.register()`
- Inherits from `BasePreprocessor`
- Produces standard `BatteryData` objects
- Can be used with existing BatteryML pipelines and models 
