#!/usr/bin/env python3
"""
Clean test script for production dual socket demo.
Tests data sharing and request tracking without verbose logs.
"""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

def test_unix_socket(path, url):
    """Test Unix socket API using curl"""
    try:
        result = subprocess.run([
            'curl', '-s', '--unix-socket', path, f'http://localhost{url}'
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return None
    except Exception as e:
        print(f"Error testing Unix socket: {e}")
        return None

def main():
    print("🧪 Production Dual Socket Test")
    print("=" * 40)
    
    # Test public API
    print("\n1. Testing Public API (HTTP)")
    print("-" * 30)
    
    try:
        # Initial state
        resp = requests.get("http://localhost:8000/data", timeout=5)
        print(f"   Initial data: {resp.json()}")
        
        # Add some data
        data = {"key": "public_test", "value": "from_worker"}
        resp = requests.post("http://localhost:8000/data", json=data, timeout=5)
        print(f"   Add data: {resp.json()}")
        
        # Verify data
        resp = requests.get("http://localhost:8000/data", timeout=5)
        print(f"   Verify data: {resp.json()}")
        
        # Multiple requests to test worker load balancing
        print("   Making 5 requests to test worker distribution...")
        for i in range(5):
            requests.get("http://localhost:8000/data", timeout=5)
            print(f"     Request {i+1} ✓")
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Public API error: {e}")
        return 1
    
    # Test admin API
    print("\n2. Testing Admin API (Unix Socket)")
    print("-" * 35)
    
    socket_path = "/tmp/fastapi-local.sock"
    if not Path(socket_path).exists():
        print(f"   ❌ Admin socket not found: {socket_path}")
        return 1
    
    # Get metrics
    metrics = test_unix_socket(socket_path, "/admin/metrics")
    if metrics:
        print(f"   Request count: {metrics.get('requests', 'Unknown')}")
        print(f"   Last access: {metrics.get('last_access', 'Unknown')}")
    else:
        print("   ❌ Failed to get metrics")
        return 1
    
    # Get all data (including private)
    all_data = test_unix_socket(socket_path, "/admin/data/all")
    if all_data:
        data_count = len(all_data.get('data', {}))
        print(f"   Total data items: {data_count}")
        print(f"   Data: {all_data.get('data', {})}")
    else:
        print("   ❌ Failed to get admin data")
        return 1
    
    # Add private data via admin
    print("   Adding private data via admin...")
    result = subprocess.run([
        'curl', '-s', '--unix-socket', socket_path,
        'http://localhost/admin/data',
        '-H', 'Content-Type: application/json',
        '-d', '{"key": "_private_key", "value": "admin_secret"}',
        '-X', 'POST'
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print(f"   Admin add: {json.loads(result.stdout)}")
    else:
        print("   ❌ Failed to add private data")
        return 1
    
    # Test data isolation
    print("\n3. Testing Data Isolation")
    print("-" * 25)
    
    # Public API should not see private data
    resp = requests.get("http://localhost:8000/data", timeout=5)
    public_data = resp.json().get('data', {})
    has_private = any(k.startswith('_') for k in public_data.keys())
    
    if has_private:
        print("   ❌ Public API can see private data!")
        return 1
    else:
        print("   ✅ Public API correctly filters private data")
    
    # Admin API should see all data
    all_data = test_unix_socket(socket_path, "/admin/data/all")
    if all_data:
        admin_data = all_data.get('data', {})
        has_private_admin = any(k.startswith('_') for k in admin_data.keys())
        if has_private_admin:
            print("   ✅ Admin API can see private data")
        else:
            print("   ⚠️  Admin API missing private data")
    
    # Final metrics check
    print("\n4. Final Request Tracking")
    print("-" * 25)
    
    final_metrics = test_unix_socket(socket_path, "/admin/metrics")
    if final_metrics:
        final_count = final_metrics.get('requests', 0)
        print(f"   Final request count: {final_count}")
        
        # We made roughly: 1 initial + 1 verify + 5 load test + several admin calls
        if final_count >= 8:
            print("   ✅ Request tracking appears to be working")
        else:
            print(f"   ⚠️  Request count seems low (expected >= 8, got {final_count})")
    
    print("\n🎉 Production test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())