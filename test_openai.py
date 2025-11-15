"""Quick test to verify OpenAI API key works."""
import asyncio
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

async def test_openai():
    try:
        from openai import AsyncOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(" OPENAI_API_KEY not found in environment")
            return False
        
        print(f" API Key found: {api_key[:20]}...")
        
        client = AsyncOpenAI(api_key=api_key)
        
        print("Testing OpenAI API...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Hello, I am working!'"}],
            max_tokens=20
        )
        
        result = response.choices[0].message.content
        print(f" OpenAI Response: {result}")
        return True
        
    except Exception as e:
        print(f" OpenAI Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai())
    exit(0 if success else 1)
