# tests/test_load.py
import asyncio
import httpx
import time
from datetime import datetime  # ← ADD THIS MISSING IMPORT
import statistics

async def load_test():
    url = "http://localhost:8000/reward/decide"
    data = {
        "txn_id": "load_test",
        "user_id": "load_user",
        "merchant_id": "load_merchant",
        "amount": 100,
        "txn_type": "PURCHASE",
        "ts": datetime.now().isoformat()  # Now works!
    }
    
    async with httpx.AsyncClient() as client:
        print("🚀 Starting load test with 300 requests...")
        start = time.time()
        tasks = []
        for i in range(300):
            data["txn_id"] = f"load_test_{i}"
            tasks.append(client.post(url, json=data.copy()))  # Use copy to avoid mutation
        
        responses = await asyncio.gather(*tasks)
        end = time.time()
        
        # Calculate metrics
        total_time = end - start
        rps = 300 / total_time
        latencies = [r.elapsed.total_seconds() * 1000 for r in responses if r.status_code == 200]
        latencies.sort()
        
        successful = len(latencies)
        print(f"\n📊 Load Test Results:")
        print(f"   ✅ Successful requests: {successful}/300")
        print(f"   ⏱️  Total time: {total_time:.2f} seconds")
        print(f"   ⚡ Requests/sec: {rps:.2f}")
        
        if successful > 0:
            p95 = latencies[int(0.95 * len(latencies))]
            p99 = latencies[int(0.99 * len(latencies))]
            print(f"   📈 p95 latency: {p95:.2f}ms")
            print(f"   📉 p99 latency: {p99:.2f}ms")
            
            if rps >= 300:
                print("\n✅ TARGET ACHIEVED: 300+ requests/sec!")
            else:
                print(f"\n⚠️  Target not met: {rps:.2f}/300 requests/sec")
        else:
            print("❌ No successful requests - is your server running?")

if __name__ == "__main__":
    # Make sure server is running before executing this!
    print("=" * 60)
    print("⚠️  IMPORTANT: Make sure your FastAPI server is running on port 8000")
    print("=" * 60)
    asyncio.run(load_test())