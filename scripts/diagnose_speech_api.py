"""
Diagnostic script to check Google Cloud Speech-to-Text API configuration.

This script will:
1. Check if credentials file exists and is valid
2. Verify the project ID in credentials
3. Test Speech-to-Text API access
4. Check Text-to-Speech API access
"""

import json
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config

def check_credentials_file():
    """Check if credentials file exists and is valid JSON."""
    print("=" * 60)
    print("1. Checking Credentials File")
    print("=" * 60)
    
    creds_paths = []
    
    # Check config.GOOGLE_APPLICATION_CREDENTIALS
    if config.GOOGLE_APPLICATION_CREDENTIALS:
        creds_path = Path(config.GOOGLE_APPLICATION_CREDENTIALS)
        if not creds_path.is_absolute():
            creds_path = project_root / creds_path
        creds_paths.append(("GOOGLE_APPLICATION_CREDENTIALS from config", creds_path))
    
    # Check default location
    default_creds = project_root / "google_creds.json"
    creds_paths.append(("Default location (google_creds.json)", default_creds))
    
    # Check environment variable
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        env_creds = Path(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])
        creds_paths.append(("GOOGLE_APPLICATION_CREDENTIALS env var", env_creds))
    
    valid_creds = None
    for name, path in creds_paths:
        print(f"\nChecking: {name}")
        print(f"  Path: {path}")
        if path.exists():
            print(f"  ✅ File exists")
            try:
                with open(path, 'r') as f:
                    creds_data = json.load(f)
                    print(f"  ✅ Valid JSON")
                    
                    # Extract project info
                    project_id = creds_data.get('project_id', 'NOT FOUND')
                    client_email = creds_data.get('client_email', 'NOT FOUND')
                    print(f"  📋 Project ID: {project_id}")
                    print(f"  📧 Service Account: {client_email}")
                    
                    # Check if it's a service account key
                    if 'type' in creds_data:
                        print(f"  📝 Type: {creds_data['type']}")
                    
                    valid_creds = (path, creds_data)
                    break
            except json.JSONDecodeError as e:
                print(f"  ❌ Invalid JSON: {e}")
            except Exception as e:
                print(f"  ❌ Error reading file: {e}")
        else:
            print(f"  ❌ File does not exist")
    
    if not valid_creds:
        print("\n❌ No valid credentials file found!")
        return None
    
    return valid_creds

def test_speech_api(creds_path):
    """Test Speech-to-Text API access."""
    print("\n" + "=" * 60)
    print("2. Testing Speech-to-Text API")
    print("=" * 60)
    
    try:
        from google.cloud import speech
        
        # Set credentials
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
        
        # Initialize client
        print("\nInitializing Speech-to-Text client...")
        client = speech.SpeechClient.from_service_account_json(str(creds_path))
        print("✅ Client initialized successfully")
        
        # Get project ID from client
        try:
            # Try to get project info
            project_id = client._client_info.project_id if hasattr(client, '_client_info') else None
            if project_id:
                print(f"📋 Client Project ID: {project_id}")
        except:
            pass
        
        # Test with a minimal audio (silence)
        print("\nTesting API with minimal audio...")
        import base64
        
        # Create a minimal WAV file (silence, 1 second, 16kHz, mono)
        # WAV header + 16000 samples of silence (0x00)
        wav_header = b'RIFF' + (16036).to_bytes(4, 'little') + b'WAVE' + b'fmt ' + (16).to_bytes(4, 'little') + (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') + (16000).to_bytes(4, 'little') + (32000).to_bytes(4, 'little') + (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little') + b'data' + (16000).to_bytes(4, 'little')
        silence = bytes(16000)  # 1 second of silence
        test_audio = wav_header + silence
        
        config_obj = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        
        audio = speech.RecognitionAudio(content=test_audio)
        
        print("Sending request to Speech-to-Text API...")
        response = client.recognize(config=config_obj, audio=audio)
        print("✅ API request successful!")
        print(f"   Response: {len(response.results)} results")
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Speech-to-Text API Error: {error_str}")
        
        # Check for specific error types
        if "403" in error_str or "SERVICE_DISABLED" in error_str:
            print("\n⚠️  API is disabled or not accessible")
            print("   Possible causes:")
            print("   1. Speech-to-Text API not enabled in the project")
            print("   2. Wrong project ID in credentials")
            print("   3. Service account doesn't have permissions")
            print("   4. Billing not enabled for the project")
        elif "401" in error_str or "UNAUTHENTICATED" in error_str:
            print("\n⚠️  Authentication failed")
            print("   Possible causes:")
            print("   1. Invalid credentials file")
            print("   2. Credentials expired")
            print("   3. Service account deleted")
        elif "PERMISSION_DENIED" in error_str:
            print("\n⚠️  Permission denied")
            print("   Possible causes:")
            print("   1. Service account doesn't have 'Cloud Speech Client' role")
            print("   2. Service account doesn't have 'Service Usage Consumer' role")
        
        return False

def test_tts_api(creds_path):
    """Test Text-to-Speech API access."""
    print("\n" + "=" * 60)
    print("3. Testing Text-to-Speech API")
    print("=" * 60)
    
    try:
        from google.cloud import texttospeech
        
        # Set credentials
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
        
        # Initialize client
        print("\nInitializing Text-to-Speech client...")
        client = texttospeech.TextToSpeechClient()
        print("✅ Client initialized successfully")
        
        # Test with minimal text
        print("\nTesting API with minimal text...")
        synthesis_input = texttospeech.SynthesisInput(text="test")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-C",
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        print("Sending request to Text-to-Speech API...")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        print("✅ API request successful!")
        print(f"   Response: {len(response.audio_content)} bytes")
        
        return True
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ Text-to-Speech API Error: {error_str}")
        
        # Check for specific error types
        if "403" in error_str or "SERVICE_DISABLED" in error_str:
            print("\n⚠️  API is disabled or not accessible")
            print("   Enable Text-to-Speech API in Google Cloud Console")
        elif "401" in error_str or "UNAUTHENTICATED" in error_str:
            print("\n⚠️  Authentication failed")
        
        return False

def main():
    """Run all diagnostics."""
    print("\n" + "=" * 60)
    print("Google Cloud Speech & TTS API Diagnostic Tool")
    print("=" * 60)
    
    # Check credentials
    creds_result = check_credentials_file()
    if not creds_result:
        print("\n❌ Cannot proceed without valid credentials")
        return
    
    creds_path, creds_data = creds_result
    
    # Test Speech API
    speech_ok = test_speech_api(creds_path)
    
    # Test TTS API
    tts_ok = test_tts_api(creds_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Credentials: ✅ Found ({creds_path})")
    print(f"Project ID: {creds_data.get('project_id', 'Unknown')}")
    print(f"Speech-to-Text API: {'✅ Working' if speech_ok else '❌ Failed'}")
    print(f"Text-to-Speech API: {'✅ Working' if tts_ok else '❌ Failed'}")
    
    if not speech_ok or not tts_ok:
        print("\n" + "=" * 60)
        print("Troubleshooting Steps")
        print("=" * 60)
        print("1. Verify the API is enabled in Google Cloud Console:")
        print("   - Speech-to-Text: https://console.cloud.google.com/apis/library/speech.googleapis.com")
        print("   - Text-to-Speech: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com")
        print(f"\n2. Verify the project ID matches: {creds_data.get('project_id', 'Unknown')}")
        print("\n3. Check service account permissions:")
        print("   - Cloud Speech Client")
        print("   - Cloud Text-to-Speech API User")
        print("   - Service Usage Consumer")
        print("\n4. Ensure billing is enabled for the project")
        print("\n5. Wait a few minutes after enabling APIs for changes to propagate")

if __name__ == "__main__":
    main()

