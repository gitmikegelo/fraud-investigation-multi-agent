"""
Export the complete synthetic dataset with all related tables.

This generates the full dataset (claims, providers, members, facilities)
and exports to CSV with optional joins for comprehensive analysis.
"""

import sys
import os
import argparse

# Add parent directory to path to import data module
sys.path.insert(0, os.path.dirname(__file__))

from data.generate_synthetic import generate_all_data


def export_full_dataset(output_dir='exported_data', joined=False):
    """
    Export the complete synthetic dataset.
    
    Args:
        output_dir: Directory to save CSV files
        joined: If True, create a joined dataset with all related info
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("🔄 Generating full synthetic dataset...")
    claims_df, providers_df, members_df, facilities_df = generate_all_data()
    
    # Export individual tables
    print("\n📁 Exporting individual tables...")
    
    claims_file = os.path.join(output_dir, 'claims.csv')
    claims_df.to_csv(claims_file, index=False)
    print(f"✅ Claims: {claims_file} ({len(claims_df)} rows)")
    
    providers_file = os.path.join(output_dir, 'providers.csv')
    providers_df.to_csv(providers_file, index=False)
    print(f"✅ Providers: {providers_file} ({len(providers_df)} rows)")
    
    members_file = os.path.join(output_dir, 'members.csv')
    members_df.to_csv(members_file, index=False)
    print(f"✅ Members: {members_file} ({len(members_df)} rows)")
    
    facilities_file = os.path.join(output_dir, 'facilities.csv')
    facilities_df.to_csv(facilities_file, index=False)
    print(f"✅ Facilities: {facilities_file} ({len(facilities_df)} rows)")
    
    if joined:
        print("\n🔗 Creating joined dataset...")
        # Join claims with all related tables
        joined_df = claims_df.copy()
        
        # Join with providers
        joined_df = joined_df.merge(
            providers_df.add_prefix('provider_'),
            left_on='provider_id',
            right_on='provider_provider_id',
            how='left'
        )
        joined_df = joined_df.drop(columns=['provider_provider_id'])
        
        # Join with members
        joined_df = joined_df.merge(
            members_df.add_prefix('member_'),
            left_on='member_id',
            right_on='member_member_id',
            how='left'
        )
        joined_df = joined_df.drop(columns=['member_member_id'])
        
        # Join with facilities
        joined_df = joined_df.merge(
            facilities_df.add_prefix('facility_'),
            left_on='facility_id',
            right_on='facility_facility_id',
            how='left'
        )
        joined_df = joined_df.drop(columns=['facility_facility_id'])
        
        # Join with referring providers (if exists)
        joined_df = joined_df.merge(
            providers_df.add_prefix('referring_'),
            left_on='referring_provider_id',
            right_on='referring_provider_id',
            how='left'
        )
        joined_df = joined_df.drop(columns=['referring_provider_id'], errors='ignore')
        
        joined_file = os.path.join(output_dir, 'claims_joined.csv')
        joined_df.to_csv(joined_file, index=False)
        print(f"✅ Joined dataset: {joined_file} ({len(joined_df)} rows, {len(joined_df.columns)} columns)")
        
        print("\n📊 Joined dataset includes:")
        print("  - Claim details (claim_id, amounts, dates, codes)")
        print("  - Provider info (specialty, region, peer_group)")
        print("  - Member info (age, gender, region)")
        print("  - Facility info (type, region)")
        print("  - Referring provider info (if applicable)")
    
    print("\n✨ Export complete!")
    print(f"\n📂 All files saved to: {os.path.abspath(output_dir)}")


def main():
    parser = argparse.ArgumentParser(description='Export full synthetic dataset to CSV')
    parser.add_argument('--output', default='exported_data',
                        help='Output directory for CSV files (default: exported_data)')
    parser.add_argument('--joined', action='store_true',
                        help='Create a joined dataset with all related tables')
    
    args = parser.parse_args()
    
    export_full_dataset(args.output, args.joined)


if __name__ == "__main__":
    main()
