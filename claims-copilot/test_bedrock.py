"""
Simple script to test AWS Bedrock connectivity with Claude 4.5 Sonnet.
"""

import os
import json
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables from .env file
load_dotenv()

def test_bedrock_connection():
    """Test AWS Bedrock connection with a simple prompt."""
    
    # Get configuration from environment variables
    region = os.getenv('AWS_REGION', 'us-east-1')
    model_id = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0')
    temperature = float(os.getenv('LLM_TEMPERATURE', '0.1'))
    
    print(f"Testing AWS Bedrock connection...")
    print(f"Region: {region}")
    print(f"Model ID: {model_id}")
    print(f"Temperature: {temperature}")
    print("-" * 60)
    
    try:
        # Create Bedrock Runtime client
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region
        )
        
        # Prepare a simple test message
        prompt = "Hello! Please respond with 'Bedrock connection successful' if you can read this."
        
        # Format the request for Claude (Anthropic format)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        print("Sending test request...")
        
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract the text response
        if 'content' in response_body and len(response_body['content']) > 0:
            assistant_message = response_body['content'][0]['text']
            print("\n✅ SUCCESS! Bedrock is working.")
            print(f"\nAssistant response:\n{assistant_message}")
            print("\n" + "-" * 60)
            print("Connection test completed successfully!")
            return True
        else:
            print("⚠️ Unexpected response format")
            print(json.dumps(response_body, indent=2))
            return False
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"\n❌ AWS Client Error:")
        print(f"Error Code: {error_code}")
        print(f"Error Message: {error_message}")
        
        if error_code == 'UnrecognizedClientException':
            print("\nTip: Check your AWS credentials (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)")
        elif error_code == 'AccessDeniedException':
            print("\nTip: Your AWS credentials don't have permission to access Bedrock")
        elif error_code == 'ResourceNotFoundException':
            print("\nTip: The model ID or region might be incorrect")
            
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️ WARNING: .env file not found!")
        print("Please copy .env.example to .env and configure your AWS credentials.")
        print()
    
    test_bedrock_connection()
