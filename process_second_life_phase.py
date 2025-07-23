#!/usr/bin/env python3
"""
Script to process all CSV battery data files in the Second_life_phase directory
"""

import sys
import os
from pathlib import Path

# Add the process_scripts directory to the path
sys.path.append(str(Path(__file__).parent / 'process_scripts'))

from preprocess_SDU import SDUPreprocessor

def process_second_life_phase():
    """
    Process all CSV files in the Second_life_phase directory
    """
    print("Processing Second Life Phase Battery Data")
    print("=" * 60)
    
    # Define paths
    data_dir = "/Users/kevinwang/Downloads/14859405/Second_life_phase"
    output_dir = "./processed_second_life_phase"
    
    # Check if data directory exists
    if not Path(data_dir).exists():
        print(f"❌ Error: Directory {data_dir} does not exist!")
        return False
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    print(f"📁 Data directory: {data_dir}")
    print(f"📁 Output directory: {output_dir}")
    
    # Count CSV files
    csv_files = list(Path(data_dir).glob("*.csv"))
    print(f"📄 Found {len(csv_files)} CSV files to process")
    
    # Initialize the preprocessor
    preprocessor = SDUPreprocessor(
        output_dir=output_dir,
        silent=False  # Show detailed progress
    )
    
    # Process CSV files
    try:
        print("\n🔄 Starting preprocessing...")
        processed_num, skipped_num = preprocessor.process(
            parentdir=data_dir
        )
        
        print(f"\n✅ Processing completed!")
        print(f"📊 Batteries processed: {processed_num}")
        print(f"⏭️  Batteries skipped: {skipped_num}")
        print(f"📁 Output saved to: {output_dir}")
        
        # List the output files
        output_files = list(Path(output_dir).glob("*.pkl"))
        print(f"\n📋 Generated {len(output_files)} processed files:")
        for i, file in enumerate(sorted(output_files)[:10]):  # Show first 10
            print(f"   {i+1}. {file.name}")
        if len(output_files) > 10:
            print(f"   ... and {len(output_files) - 10} more files")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = process_second_life_phase()
    if success:
        print("\n🎉 Second life phase data preprocessing completed successfully!")
    else:
        print("\n💥 Second life phase data preprocessing failed!")
        sys.exit(1) 