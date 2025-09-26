# """
# Test script for authentication endpoints
# Run this after starting your server to test all auth functionality
# """

# import requests
# import json
# from typing import Dict, Optional


# class AuthTester:
#     def __init__(self, base_url: str = "http://localhost:8000"):
#         self.base_url = base_url
#         self.session = requests.Session()
#         self.access_token: Optional[str] = None
#         self.refresh_token: Optional[str] = None

#     def set_auth_header(self, token: str):
#         """Set Authorization header for authenticated requests"""
#         self.session.headers.update({"Authorization": f"Bearer {token}"})

#     def clear_auth_header(self):
#         """Clear Authorization header"""
#         if "Authorization" in self.session.headers:
#             del self.session.headers["Authorization"]

#     def test_health_check(self):
#         """Test health check endpoint"""
#         print("🔄 Testing health check...")

#         try:
#             response = self.session.get(f"{self.base_url}/health")

#             if response.status_code == 200:
#                 print("✅ Health check passed")
#                 return True
#             else:
#                 print(f"❌ Health check failed: {response.status_code}")
#                 return False

#         except Exception as e:
#             print(f"❌ Health check error: {str(e)}")
#             return False

#     def test_register(self, user_data: Dict):
#         """Test user registration"""
#         print("🔄 Testing user registration...")

#         try:
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/auth/register", json=user_data
#             )

#             print(f"Status Code: {response.status_code}")
#             print(f"Response: {response.json()}")

#             if response.status_code == 201:
#                 print("✅ Registration successful")
#                 return True, response.json()
#             else:
#                 print("❌ Registration failed")
#                 return False, response.json()

#         except Exception as e:
#             print(f"❌ Registration error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_login(self, login_data: Dict):
#         """Test user login"""
#         print("🔄 Testing user login...")

#         try:
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/auth/login", json=login_data
#             )

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Login successful")

#                 # Store tokens
#                 tokens = result.get("tokens", {})
#                 self.access_token = tokens.get("access_token")
#                 self.refresh_token = tokens.get("refresh_token")

#                 if self.access_token:
#                     self.set_auth_header(self.access_token)

#                 return True, result
#             else:
#                 print("❌ Login failed")
#                 return False, result

#         except Exception as e:
#             print(f"❌ Login error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_get_profile(self):
#         """Test get current user profile"""
#         print("🔄 Testing get user profile...")

#         try:
#             response = self.session.get(f"{self.base_url}/api/v1/auth/me")

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Profile retrieval successful")
#                 return True, result
#             else:
#                 print("❌ Profile retrieval failed")
#                 return False, result

#         except Exception as e:
#             print(f"❌ Profile retrieval error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_update_profile(self, update_data: Dict):
#         """Test profile update"""
#         print("🔄 Testing profile update...")

#         try:
#             response = self.session.put(
#                 f"{self.base_url}/api/v1/auth/profile", json=update_data
#             )

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Profile update successful")
#                 return True, result
#             else:
#                 print("❌ Profile update failed")
#                 return False, result

#         except Exception as e:
#             print(f"❌ Profile update error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_change_password(self, password_data: Dict):
#         """Test password change"""
#         print("🔄 Testing password change...")

#         try:
#             response = self.session.post(
#                 f"{self.base_url}/api/v1/auth/change-password", json=password_data
#             )

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Password change successful")
#                 return True, result
#             else:
#                 print("❌ Password change failed")
#                 return False, result

#         except Exception as e:
#             print(f"❌ Password change error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_refresh_token(self):
#         """Test token refresh"""
#         print("🔄 Testing token refresh...")

#         if not self.refresh_token:
#             print("❌ No refresh token available")
#             return False, {"error": "No refresh token"}

#         try:
#             # Set refresh token as auth header
#             old_header = self.session.headers.get("Authorization")
#             self.session.headers.update(
#                 {"Authorization": f"Bearer {self.refresh_token}"}
#             )

#             response = self.session.post(f"{self.base_url}/api/v1/auth/refresh")

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Token refresh successful")

#                 # Update tokens
#                 self.access_token = result.get("access_token")
#                 self.refresh_token = result.get("refresh_token")

#                 if self.access_token:
#                     self.set_auth_header(self.access_token)

#                 return True, result
#             else:
#                 print("❌ Token refresh failed")
#                 # Restore old auth header
#                 if old_header:
#                     self.session.headers.update({"Authorization": old_header})
#                 return False, result

#         except Exception as e:
#             print(f"❌ Token refresh error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_protected_endpoint(self):
#         """Test access to protected endpoint"""
#         print("🔄 Testing protected endpoint...")

#         try:
#             response = self.session.get(f"{self.base_url}/api/v1/courses")

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Protected endpoint access successful")
#                 return True, result
#             else:
#                 print("❌ Protected endpoint access failed")
#                 return False, result

#         except Exception as e:
#             print(f"❌ Protected endpoint error: {str(e)}")
#             return False, {"error": str(e)}

#     def test_logout(self):
#         """Test logout"""
#         print("🔄 Testing logout...")

#         try:
#             response = self.session.post(f"{self.base_url}/api/v1/auth/logout")

#             print(f"Status Code: {response.status_code}")
#             result = response.json()
#             print(f"Response: {json.dumps(result, indent=2)}")

#             if response.status_code == 200:
#                 print("✅ Logout successful")
#                 self.clear_auth_header()
#                 self.access_token = None
#                 self.refresh_token = None
#                 return True, result
#             else:
#                 print("❌ Logout failed")
#                 return False, result

#         except Exception as e:
#             print(f"❌ Logout error: {str(e)}")
#             return False, {"error": str(e)}


# def run_comprehensive_test():
#     """Run comprehensive authentication tests"""
#     print("🚀 Starting comprehensive authentication tests...\n")

#     tester = AuthTester()

#     # Test data
#     test_user = {
#         "name": "Test User",
#         "email": "testuser@example.com",
#         "phone": "+919876543210",
#         "password": "TestPassword123!",
#         "preferred_exam_categories": ["medical", "engineering"],
#     }

#     login_data = {"email": test_user["email"], "password": test_user["password"]}

#     # Run tests
#     tests_passed = 0
#     total_tests = 0

#     # 1. Health check
#     total_tests += 1
#     if tester.test_health_check():
#         tests_passed += 1
#     print()

#     # 2. Registration
#     total_tests += 1
#     success, _ = tester.test_register(test_user)
#     if success:
#         tests_passed += 1
#     print()

#     # 3. Login
#     total_tests += 1
#     success, _ = tester.test_login(login_data)
#     if success:
#         tests_passed += 1
#     print()

#     # 4. Get profile
#     total_tests += 1
#     if tester.test_get_profile()[0]:
#         tests_passed += 1
#     print()

#     # 5. Update profile
#     total_tests += 1
#     update_data = {"name": "Updated Test User"}
#     if tester.test_update_profile(update_data)[0]:
#         tests_passed += 1
#     print()

#     # 6. Protected endpoint
#     total_tests += 1
#     if tester.test_protected_endpoint()[0]:
#         tests_passed += 1
#     print()

#     # 7. Token refresh
#     total_tests += 1
#     if tester.test_refresh_token()[0]:
#         tests_passed += 1
#     print()

#     # 8. Change password
#     total_tests += 1
#     password_data = {
#         "current_password": test_user["password"],
#         "new_password": "NewPassword123!",
#     }
#     if tester.test_change_password(password_data)[0]:
#         tests_passed += 1
#     print()

#     # 9. Logout
#     total_tests += 1
#     if tester.test_logout()[0]:
#         tests_passed += 1
#     print()

#     # Summary
#     print("=" * 50)
#     print(f"🎯 Test Results: {tests_passed}/{total_tests} tests passed")

#     if tests_passed == total_tests:
#         print("🎉 All tests passed! Authentication system is working correctly.")
#     else:
#         print("⚠️  Some tests failed. Please check the issues above.")

#     print("=" * 50)


# if __name__ == "__main__":
#     run_comprehensive_test()
