import httpx
import asyncio

async def test_live_character_gateway_stream():
    print("🚀 INITIALIZING PHASE 10.4 ASYNC EVENT-STREAM SOCKET CHECKS...")
    
    # 🎯 THE FIX 1: Change 'localhost' to '127.0.0.1' to prevent Windows IPv6 loopback routing drops
    url = "http://127.0.0.1:8000/api/v1/query/stream"
    
    # 🎯 THE FIX 2: Change the dictionary key from "question" to "query" to match your Pydantic schema
    payload = {"query": "What is the maximum safety threshold limitation and PSI ceiling tolerance for PUMP-102?"}
    
    timeout_config = httpx.Timeout(60.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout_config) as network_client:
        try:
            async with network_client.stream("POST", url, json=payload) as stream_channel:
                if stream_channel.status_code != 200:
                    print(f"❌ ROUTE REJECTED: Server returned status code {stream_channel.status_code}")
                    # If it returns a validation error, read out the server text to debug
                    error_body = await stream_channel.aread()
                    print(f"   Details: {error_body.decode()}")
                    return

                print("\n🌊 GATEWAY PIPELINE CONNECTED! STREAMING TOKENS IN REAL-TIME:\n")
                print("-" * 80)
                
                async_generator = stream_channel.aiter_lines()
                async for event_line in async_generator:
                    if event_line.startswith("data: "):
                        clean_token = event_line.replace("data: ", "")
                        print(clean_token, end=" ", flush=True)
                        
                print("\n\n" + "-" * 80)
                print("🟢 EVENT STREAM COMPLETE: Long-lived socket channel closed cleanly.")
                
        except Exception as exc:
            print(f"❌ STREAM READER CONNECTION FAULT: {str(exc)}")
            print("💡 TIP: Verify your Uvicorn server window is active, running, and didn't crash due to an import typo.")

if __name__ == "__main__":
    asyncio.run(test_live_character_gateway_stream())