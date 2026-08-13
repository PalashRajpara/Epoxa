import os
import sys
from dotenv import load_dotenv

# 1. Load the environment variables from the root .env file
# Since this file sits in ai-voice-agent/agent/config.py,
# the parent of agent is the root directory containing the .env file.
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path, override=True)

# 2. Define the list of required environment variables for the Agent
REQUIRED_ENV_VARS = {
    "LIVEKIT_URL": "LiveKit Cloud connection URL",
    "LIVEKIT_API_KEY": "LiveKit API Key",
    "LIVEKIT_API_SECRET": "LiveKit API Secret",
    "GROQ_API_KEY": "Groq LLM API Key (using openai plugin model configuration)",
    "DEEPGRAM_STT_API_KEY": "Deepgram Speech-to-Text API Key",
    "DEEPGRAM_TTS_API_KEY": "Deepgram Text-to-Speech API Key"
}

def validate_config():
    """
    Checks that all required credentials are present.
    If any variables are missing, prints a beginner-friendly help message and exits.
    """
    missing_vars = []
    for var_name, description in REQUIRED_ENV_VARS.items():
        val = os.getenv(var_name)
        if not val or val.startswith("your-") or val.startswith("wss://your-") or val.endswith("-key"):
            missing_vars.append((var_name, description))
            
    if missing_vars:
        print("\n" + "=" * 60)
        print("❌ CONFIGURATION ERROR: Missing or default environment variables!")
        print("=" * 60)
        print("The following API keys are not set correctly in your root '.env' file:\n")
        
        for name, desc in missing_vars:
            print(f"  • {name}: {desc}")
            
        print("\nHow to fix:")
        print("  1. Open the file: '.env' at the root of the project")
        print("  2. Replace the placeholder values with your real API keys")
        print("  3. Restart this process")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    print("✅ Configuration validation passed. All required keys are set.")

# 3. Expose configuration values for easy access in our main agent code
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPGRAM_STT_API_KEY = os.getenv("DEEPGRAM_STT_API_KEY")
DEEPGRAM_TTS_API_KEY = os.getenv("DEEPGRAM_TTS_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")

class Settings:
    def __init__(self):
        self.LIVEKIT_URL = LIVEKIT_URL
        self.LIVEKIT_API_KEY = LIVEKIT_API_KEY
        self.LIVEKIT_API_SECRET = LIVEKIT_API_SECRET
        self.GROQ_API_KEY = GROQ_API_KEY
        self.DEEPGRAM_STT_API_KEY = DEEPGRAM_STT_API_KEY
        self.DEEPGRAM_TTS_API_KEY = DEEPGRAM_TTS_API_KEY
        self.CARTESIA_API_KEY = CARTESIA_API_KEY
        
    def validate_config(self):
        validate_config()

settings = Settings()
