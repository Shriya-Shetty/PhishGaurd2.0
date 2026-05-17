import requests
import json

def test_backend():
    """Test if the backend is running and responding correctly"""
    url = "http://127.0.0.1:5000/classify"
    
    # Test data
    test_data = {
        "email_text": "Urgent: Verify your account immediately! Click here to avoid suspension.",
        "email_address": "security@paypa1.com"  # Intentionally misspelled
    }
    
    try:
        print(f"Testing backend at {url}")
        response = requests.post(url, json=test_data, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print("+ Backend is responding correctly:")
            print(f"  Classification: {result.get('classification')}")
            print(f"  Probability: {result.get('probability')}")
            print(f"  Risk Score: {result.get('risk_score')}")
            return True
        else:
            print(f"x Backend returned status code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("x Cannot connect to backend. Make sure Flask app is running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"x Error testing backend: {e}")
        return False

if __name__ == "__main__":
    test_backend()