"""Test Bedrock model connectivity and availability."""
import os
import boto3
from dotenv import load_dotenv

# Force reload env
load_dotenv(override=True)

model_id = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-haiku-4-5-20251001-v1:0')
region = os.getenv('AWS_REGION', 'us-east-1')

print(f"Testing model: {model_id}")
print(f"Region: {region}")
print("-" * 50)

client = boto3.client('bedrock-runtime', region_name=region)

try:
    response = client.converse(
        modelId=model_id,
        messages=[
            {"role": "user", "content": [{"text": "Say hello in one word."}]}
        ],
        inferenceConfig={"maxTokens": 50, "temperature": 0.1}
    )
    output = response['output']['message']['content'][0]['text']
    print(f"SUCCESS! Response: {output}")
except Exception as e:
    print(f"ERROR: {e}")
    print("\nTrying alternative model IDs...")
    
    # Try different model ID formats (use us. prefix for inference profiles)
    alternatives = [
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    ]
    
    for alt_model in alternatives:
        if alt_model == model_id:
            continue
        try:
            print(f"\nTrying: {alt_model}")
            response = client.converse(
                modelId=alt_model,
                messages=[
                    {"role": "user", "content": [{"text": "Say hello in one word."}]}
                ],
                inferenceConfig={"maxTokens": 100, "temperature": 0.1}
            )
            output = response['output']['message']['content'][0]['text']
            print(f"  SUCCESS! Response: {output}")
            print(f"\n>>> UPDATE .env to use: BEDROCK_MODEL_ID={alt_model}")
            break
        except Exception as e2:
            print(f"  Failed: {e2}")
