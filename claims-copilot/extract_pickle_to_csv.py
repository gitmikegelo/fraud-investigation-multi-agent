"""
Extract fraud_cache.pkl to CSV files.

This script reads the pickled fraud data and exports it to CSV format.
You can choose to export each fraud type separately or combined.
"""

import pickle
import pandas as pd
import os
import argparse


def extract_pickle_to_csv(pickle_path=None, output_dir='exported_data', combined=False):
    """
    Extract pickle file to CSV.
    
    Args:
        pickle_path: Path to the pickle file
        output_dir: Directory to save CSV files
        combined: If True, combine all fraud types into one CSV. If False, create separate CSVs.
    """
    # Default to fraud_cache.pkl in the same directory as this script
    if pickle_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pickle_path = os.path.join(script_dir, 'fraud_cache.pkl')
    
    # Ensure pickle file exists
    if not os.path.exists(pickle_path):
        print(f"Error: {pickle_path} not found!")
        return
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load pickle file
    print(f"Loading {pickle_path}...")
    with open(pickle_path, 'rb') as f:
        fraud_data = pickle.load(f)
    
    print(f"Found {len(fraud_data)} fraud categories:")
    for key in fraud_data.keys():
        print(f"  - {key}: {len(fraud_data[key])} claims")
    
    if combined:
        # Combine all DataFrames into one
        print("\nCombining all fraud types...")
        all_dfs = []
        for fraud_type, df in fraud_data.items():
            # Add fraud_type column to identify the source
            df_copy = df.copy()
            df_copy['fraud_type'] = fraud_type
            all_dfs.append(df_copy)
        
        combined_df = pd.concat(all_dfs, ignore_index=True)
        output_file = os.path.join(output_dir, 'fraud_data_combined.csv')
        combined_df.to_csv(output_file, index=False)
        print(f"✅ Exported combined data to: {output_file}")
        print(f"   Total claims: {len(combined_df)}")
    else:
        # Export each fraud type separately
        print("\nExporting each fraud type to separate CSV...")
        for fraud_type, df in fraud_data.items():
            output_file = os.path.join(output_dir, f'fraud_data_{fraud_type}.csv')
            df.to_csv(output_file, index=False)
            print(f"✅ Exported {fraud_type}: {output_file} ({len(df)} claims)")
    
    print("\n✨ Export complete!")


def main():
    parser = argparse.ArgumentParser(description='Extract fraud_cache.pkl to CSV files')
    parser.add_argument('--pickle', default=None, 
                        help='Path to pickle file (default: fraud_cache.pkl in script directory)')
    parser.add_argument('--output', default='exported_data',
                        help='Output directory for CSV files (default: exported_data)')
    parser.add_argument('--combined', action='store_true',
                        help='Combine all fraud types into one CSV file')
    
    args = parser.parse_args()
    
    extract_pickle_to_csv(args.pickle, args.output, args.combined)


if __name__ == "__main__":
    main()
