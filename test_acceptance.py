#!/usr/bin/env python3
"""
Acceptance Criteria Testing untuk Windows.
"""
import asyncio
import httpx
import json
import sys

API_BASE = "http://localhost:8000"
AUTH = {"Authorization": "Bearer devkey"}


class TestRunner:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def log(self, name, passed, details=""):
        status = " PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
        if details:
            print(f"   {details}")
        self.results.append((name, passed, details))
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    async def run_all(self):
        print("\n" + "="*80)
        print("ACCEPTANCE CRITERIA TESTING (Windows)")
        print("="*80 + "\n")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self.test_streaming(client)
            await self.test_context_aware(client)
            await self.test_db_tools(client)
            await self.test_persistence(client)
        
        print("\n" + "="*80)
        print(f"RESULTS: {self.passed}/{self.passed+self.failed} passed")
        print("="*80 + "\n")
        
        return self.failed == 0
    
    async def test_streaming(self, client):
        print("[TEST 1] Streaming Events")
        print("-"*80)
        
        events = {"agent": 0, "tool_call_started": 0, "tool_call_completed": 0, 
                  "token": 0, "done": 0}
        
        payload = {"sessionId": "test1", "userId": "u1", "prompt": "Hello"}
        
        async with client.stream(
            "POST", f"{API_BASE}/v1/chat/stream",
            headers={**AUTH, "Content-Type": "application/json"},
            json=payload
        ) as resp:
            event_type = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    if event_type in events:
                        events[event_type] += 1
        
        all_present = all(v > 0 for v in events.values())
        self.log("Streaming: All event types present", all_present,
                f"Events: {events}")
        print()
    
    async def test_context_aware(self, client):
        print("[TEST 2] Context-Aware Memory")
        print("-"*80)
        
        session_id = "test2"
        
        # Turn 1
        await self._chat(client, session_id, "My favorite color is blue")
        await asyncio.sleep(1)
        
        # Turn 2
        text = await self._chat(client, session_id, "What color did I mention?")
        
        remembers = "blue" in text.lower()
        self.log("Context: Remembers previous turn", remembers)
        
        resp = await client.get(f"{API_BASE}/v1/sessions/{session_id}")
        data = resp.json() if resp.status_code == 200 else {}
        self.log("Context: Session tracks messages", 
                data.get('messageCount', 0) >= 2,
                f"Count: {data.get('messageCount', 0)}")
        print()
    
    async def test_db_tools(self, client):
        print("[TEST 3] DB Tool Calling")
        print("-"*80)
        
        session_id = "test3"
        events = await self._chat_events(client, session_id, "Show my history")
        
        has_tool_start = any(e[0] == "tool_call_started" for e in events)
        has_tool_end = any(e[0] == "tool_call_completed" for e in events)
        
        self.log("DB Tools: Worker invokes tools", 
                has_tool_start and has_tool_end)
        
        await asyncio.sleep(1)
        resp = await client.get(f"{API_BASE}/v1/metrics/{session_id}")
        data = resp.json() if resp.status_code == 200 else {}
        self.log("DB Tools: Tool calls logged", 
                data.get('totalToolCalls', 0) > 0,
                f"Count: {data.get('totalToolCalls', 0)}")
        print()
    
    async def test_persistence(self, client):
        print("[TEST 4] Persistence")
        print("-"*80)
        
        session_id = "test4"
        events = await self._chat_events(client, session_id, "Explain AI")
        
        done_data = next((e[1] for e in events if e[0] == "done"), None)
        
        if done_data:
            timings = done_data.get('timings', {})
            suggestions = done_data.get('suggestions', [])
            
            self.log("Persistence: TTFT present", 
                    timings.get('ttft_ms') is not None,
                    f"TTFT: {timings.get('ttft_ms')}ms")
            self.log("Persistence: Total time present",
                    timings.get('total_ms') is not None,
                    f"Total: {timings.get('total_ms')}ms")
            self.log("Persistence: 3 suggestions",
                    len(suggestions) == 3)
        
        await asyncio.sleep(1)
        resp = await client.get(f"{API_BASE}/v1/sessions/{session_id}/messages")
        messages = resp.json() if resp.status_code == 200 else []
        self.log("Persistence: Messages stored",
                len(messages) >= 2,
                f"Count: {len(messages)}")
        print()
    
    async def _chat(self, client, session_id, prompt):
        tokens = []
        payload = {"sessionId": session_id, "userId": "u1", "prompt": prompt}
        
        async with client.stream(
            "POST", f"{API_BASE}/v1/chat/stream",
            headers={**AUTH, "Content-Type": "application/json"},
            json=payload
        ) as resp:
            event_type = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    if event_type == "token":
                        try:
                            data = json.loads(line.split(":", 1)[1].strip())
                            tokens.append(data.get('text', ''))
                        except:
                            pass
        return ''.join(tokens)
    
    async def _chat_events(self, client, session_id, prompt):
        events = []
        payload = {"sessionId": session_id, "userId": "u1", "prompt": prompt}
        
        async with client.stream(
            "POST", f"{API_BASE}/v1/chat/stream",
            headers={**AUTH, "Content-Type": "application/json"},
            json=payload
        ) as resp:
            event_type = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    try:
                        data = json.loads(line.split(":", 1)[1].strip())
                        events.append((event_type, data))
                    except:
                        pass
        return events


async def main():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE}/health")
            if resp.status_code != 200:
                print("Backend not healthy")
                return 1
    except:
        print("Cannot connect. Run: docker-compose up -d")
        return 1
    
    runner = TestRunner()
    success = await runner.run_all()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
