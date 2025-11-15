#!/usr/bin/env python3
"""
Seed script untuk testing context-aware behavior di Windows.
"""
import asyncio
import httpx
import json

API_BASE = "http://localhost:8000"
AUTH = {"Authorization": "Bearer devkey"}


async def stream_chat(client, session_id, user_id, prompt):
    """Make a streaming chat request."""
    print(f"\n User: {prompt}\n Assistant: ", end='', flush=True)
    
    payload = {"sessionId": session_id, "userId": user_id, "prompt": prompt}
    
    async with client.stream(
        "POST",
        f"{API_BASE}/v1/chat/stream",
        headers={**AUTH, "Content-Type": "application/json"},
        json=payload,
        timeout=60.0
    ) as resp:
        event_type = None
        async for line in resp.aiter_lines():
            if not line.strip():
                continue
            
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                    if event_type == "token":
                        print(data.get('text', ''), end='', flush=True)
                    elif event_type == "done":
                        print("\n")
                        timings = data.get('timings', {})
                        print(f"  TTFT: {timings.get('ttft_ms', 0):.1f}ms | "
                              f"Total: {timings.get('total_ms', 0):.1f}ms")
                        print(f"  Suggestions:")
                        for i, sug in enumerate(data.get('suggestions', []), 1):
                            print(f"     {i}. {sug}")
                except:
                    pass


async def main():
    print("\n" + "="*70)
    print(" SEED SCRIPT - Testing Context-Aware Memory (Windows)")
    print("="*70)
    
    async with httpx.AsyncClient() as client:
        # Health check
        try:
            resp = await client.get(f"{API_BASE}/health", timeout=5.0)
            if resp.status_code != 200:
                print(" Backend not healthy. Run: docker-compose up -d")
                return
            print(" Backend is healthy\n")
        except:
            print(" Cannot connect to backend.")
            print("Run: docker-compose up -d")
            return
        
        session_id = "seed_session_1"
        user_id = "test_user"
        
        # Turn 1
        print("\n TURN 1: Establishing context")
        print("-"*70)
        await stream_chat(client, session_id, user_id, 
                         "My name is Kurnia Anwar Ra'if and I'm learning Python.")
        await asyncio.sleep(2)
        
        # Turn 2
        print("\n TURN 2: Testing context awareness")
        print("-"*70)
        await stream_chat(client, session_id, user_id,
                         "What's my name?")
        await asyncio.sleep(2)
        
        # Turn 3
        print("\n TURN 3: Full conversation summary")
        print("-"*70)
        await stream_chat(client, session_id, user_id,
                         "Summarize our conversation.")
        
        # Verification
        print("\n" + "="*70)
        print(" VERIFICATION")
        print("="*70)
        
        resp = await client.get(f"{API_BASE}/v1/sessions/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n Session: {data['sessionId']}")
            print(f"  - Messages: {data['messageCount']}")
            print(f"  - Has Summary: {data['summary'] is not None}")
        
        resp = await client.get(f"{API_BASE}/v1/metrics/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n Metrics:")
            print(f"  - Total Requests: {data['totalRequests']}")
            print(f"  - Avg TTFT: {data.get('avgTtftMs', 0):.1f}ms")
            print(f"  - Tool Calls: {data['totalToolCalls']}")
        
        print("\n" + "="*70)
        print("SEED COMPLETED")
        print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
