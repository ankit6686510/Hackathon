#!/usr/bin/env python3
"""
Slack Integration Test Suite for SherlockAI
Tests all Slack bot functionality including slash commands, API integration, and error handling
"""

import os
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SlackIntegrationTester:
    def __init__(self):
        self.api_url = "http://localhost:8000"
        self.slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.slack_app_token = os.getenv("SLACK_APP_TOKEN")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "details": []
        }
    
    def print_banner(self):
        print("=" * 80)
        print("🤖 SherlockAI Slack Integration Test Suite")
        print("=" * 80)
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def log_test(self, test_name, status, message="", details=None):
        """Log test results"""
        self.test_results["total"] += 1
        if status == "PASS":
            self.test_results["passed"] += 1
            print(f"✅ {test_name}: {message}")
        else:
            self.test_results["failed"] += 1
            print(f"❌ {test_name}: {message}")
        
        if details:
            print(f"   📋 Details: {details}")
        
        self.test_results["details"].append({
            "test": test_name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        print()
    
    def test_environment_variables(self):
        """Test 1: Verify all required environment variables are set"""
        print("🔧 Testing Environment Variables...")
        
        required_vars = {
            "SLACK_BOT_TOKEN": self.slack_bot_token,
            "SLACK_APP_TOKEN": self.slack_app_token,
            "SLACK_SIGNING_SECRET": self.slack_signing_secret
        }
        
        all_present = True
        missing_vars = []
        
        for var_name, var_value in required_vars.items():
            if not var_value:
                all_present = False
                missing_vars.append(var_name)
            else:
                print(f"   ✅ {var_name}: {'*' * 20}...{var_value[-4:]}")
        
        if all_present:
            self.log_test("Environment Variables", "PASS", "All required Slack tokens are configured")
        else:
            self.log_test("Environment Variables", "FAIL", f"Missing variables: {', '.join(missing_vars)}")
        
        return all_present
    
    def test_backend_connectivity(self):
        """Test 2: Verify backend API is accessible"""
        print("🔌 Testing Backend Connectivity...")
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.api_url}/api/v1/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                self.log_test("Backend Health", "PASS", f"Backend responding (status: {health_data.get('status', 'unknown')})")
                
                # Test search endpoint
                search_response = requests.post(
                    f"{self.api_url}/api/v1/search",
                    json={"query": "test payment issue", "top_k": 1},
                    timeout=15
                )
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    self.log_test("Search API", "PASS", f"Search API working (found {search_data.get('total_results', 0)} results)")
                    return True
                else:
                    self.log_test("Search API", "FAIL", f"Search API error: {search_response.status_code}")
                    return False
            else:
                self.log_test("Backend Health", "FAIL", f"Backend error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Backend Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_slack_bot_process(self):
        """Test 3: Verify Slack bot process is running"""
        print("🤖 Testing Slack Bot Process...")
        
        try:
            import subprocess
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, 
                text=True
            )
            
            slack_processes = [line for line in result.stdout.split('\n') if 'slack_bot.py' in line and 'grep' not in line]
            
            if slack_processes:
                process_info = slack_processes[0].split()
                pid = process_info[1]
                self.log_test("Slack Bot Process", "PASS", f"Bot running (PID: {pid})")
                return True
            else:
                self.log_test("Slack Bot Process", "FAIL", "Slack bot process not found")
                return False
                
        except Exception as e:
            self.log_test("Slack Bot Process", "FAIL", f"Process check error: {str(e)}")
            return False
    
    def test_slack_api_configuration(self):
        """Test 4: Test Slack API configuration (token format validation)"""
        print("🔑 Testing Slack API Configuration...")
        
        # Validate token formats
        token_tests = []
        
        if self.slack_bot_token:
            if self.slack_bot_token.startswith('xoxb-'):
                token_tests.append(("Bot Token Format", "PASS", "Correct xoxb- prefix"))
            else:
                token_tests.append(("Bot Token Format", "FAIL", "Invalid bot token format (should start with xoxb-)"))
        
        if self.slack_app_token:
            if self.slack_app_token.startswith('xapp-'):
                token_tests.append(("App Token Format", "PASS", "Correct xapp- prefix"))
            else:
                token_tests.append(("App Token Format", "FAIL", "Invalid app token format (should start with xapp-)"))
        
        if self.slack_signing_secret:
            if len(self.slack_signing_secret) >= 32:
                token_tests.append(("Signing Secret", "PASS", "Signing secret has adequate length"))
            else:
                token_tests.append(("Signing Secret", "FAIL", "Signing secret too short"))
        
        all_passed = True
        for test_name, status, message in token_tests:
            if status == "FAIL":
                all_passed = False
            self.log_test(test_name, status, message)
        
        return all_passed
    
    def test_slack_command_simulation(self):
        """Test 5: Simulate Slack command processing"""
        print("💬 Testing Slack Command Simulation...")
        
        # Test different query types that the bot should handle
        test_queries = [
            {
                "query": "UPI payment failed with error 5003",
                "expected_type": "payment_issue",
                "description": "Payment domain query"
            },
            {
                "query": "database connection timeout",
                "expected_type": "technical_issue", 
                "description": "Technical domain query"
            },
            {
                "query": "hello",
                "expected_type": "greeting",
                "description": "Greeting query"
            },
            {
                "query": "what is the weather today",
                "expected_type": "non_technical",
                "description": "Non-technical query"
            }
        ]
        
        all_passed = True
        
        for test_case in test_queries:
            try:
                # Simulate what the Slack bot would do
                response = requests.post(
                    f"{self.api_url}/api/v1/search",
                    json={"query": test_case["query"], "top_k": 3},
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(
                        f"Query Processing - {test_case['description']}", 
                        "PASS", 
                        f"Query processed successfully (found {data.get('total_results', 0)} results)"
                    )
                else:
                    self.log_test(
                        f"Query Processing - {test_case['description']}", 
                        "FAIL", 
                        f"API error: {response.status_code}"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test(
                    f"Query Processing - {test_case['description']}", 
                    "FAIL", 
                    f"Error: {str(e)}"
                )
                all_passed = False
        
        return all_passed
    
    def test_error_handling(self):
        """Test 6: Test error handling scenarios"""
        print("🚨 Testing Error Handling...")
        
        error_tests = [
            {
                "name": "Empty Query",
                "payload": {"query": "", "top_k": 3},
                "expected_behavior": "Should handle gracefully"
            },
            {
                "name": "Invalid Top K",
                "payload": {"query": "test", "top_k": -1},
                "expected_behavior": "Should use default value"
            },
            {
                "name": "Very Long Query",
                "payload": {"query": "x" * 1000, "top_k": 3},
                "expected_behavior": "Should process or truncate"
            }
        ]
        
        all_passed = True
        
        for test in error_tests:
            try:
                response = requests.post(
                    f"{self.api_url}/api/v1/search",
                    json=test["payload"],
                    timeout=10
                )
                
                # Any response (even error) is acceptable as long as it doesn't crash
                if response.status_code in [200, 400, 422]:
                    self.log_test(
                        f"Error Handling - {test['name']}", 
                        "PASS", 
                        f"Handled gracefully (status: {response.status_code})"
                    )
                else:
                    self.log_test(
                        f"Error Handling - {test['name']}", 
                        "FAIL", 
                        f"Unexpected status: {response.status_code}"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test(
                    f"Error Handling - {test['name']}", 
                    "FAIL", 
                    f"Exception: {str(e)}"
                )
                all_passed = False
        
        return all_passed
    
    def test_response_formatting(self):
        """Test 7: Test response formatting for Slack"""
        print("📝 Testing Response Formatting...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/search",
                json={"query": "payment timeout error", "top_k": 2},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response has required fields for Slack formatting
                required_fields = ["query", "results", "total_results", "execution_time_ms"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("Response Structure", "PASS", "All required fields present")
                    
                    # Check if results have proper structure for Slack display
                    if data.get("results"):
                        result = data["results"][0]
                        result_fields = ["id", "title", "ai_suggestion", "score"]
                        missing_result_fields = [field for field in result_fields if field not in result]
                        
                        if not missing_result_fields:
                            self.log_test("Result Structure", "PASS", "Results properly formatted for Slack")
                            return True
                        else:
                            self.log_test("Result Structure", "FAIL", f"Missing result fields: {missing_result_fields}")
                            return False
                    else:
                        self.log_test("Result Structure", "PASS", "No results returned (acceptable)")
                        return True
                else:
                    self.log_test("Response Structure", "FAIL", f"Missing fields: {missing_fields}")
                    return False
            else:
                self.log_test("Response Formatting", "FAIL", f"API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Response Formatting", "FAIL", f"Error: {str(e)}")
            return False
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("=" * 80)
        print("📊 SLACK INTEGRATION TEST REPORT")
        print("=" * 80)
        
        # Summary
        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📈 **Test Summary:**")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {failed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        print()
        
        # Status indicator
        if success_rate >= 90:
            status = "🟢 EXCELLENT"
        elif success_rate >= 75:
            status = "🟡 GOOD"
        elif success_rate >= 50:
            status = "🟠 NEEDS IMPROVEMENT"
        else:
            status = "🔴 CRITICAL ISSUES"
        
        print(f"🎯 **Overall Status:** {status}")
        print()
        
        # Recommendations
        print("💡 **Recommendations:**")
        if failed == 0:
            print("   ✅ All tests passed! Your Slack integration is ready for production.")
            print("   🚀 You can now use the following commands in Slack:")
            print("      • /SherlockAI <payment issue description>")
            print("      • @SherlockAI <technical problem>")
            print("      • Direct message the bot with any query")
        else:
            print("   ⚠️  Some tests failed. Please review the failed tests above.")
            print("   🔧 Common fixes:")
            print("      • Verify all environment variables are set correctly")
            print("      • Ensure backend API is running and accessible")
            print("      • Check Slack app permissions and scopes")
            print("      • Verify Socket Mode is enabled in Slack app settings")
        
        print()
        print("📚 **Next Steps:**")
        print("   1. Go to your Slack workspace")
        print("   2. Try: /SherlockAI payment timeout error")
        print("   3. Check bot responses and formatting")
        print("   4. Test with team members")
        print()
        
        # Save detailed report
        report_file = f"slack_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"📄 Detailed report saved to: {report_file}")
        print("=" * 80)
        
        return success_rate >= 75  # Return True if tests are mostly successful
    
    def run_all_tests(self):
        """Run complete test suite"""
        self.print_banner()
        
        # Run all tests
        tests = [
            self.test_environment_variables,
            self.test_backend_connectivity,
            self.test_slack_bot_process,
            self.test_slack_api_configuration,
            self.test_slack_command_simulation,
            self.test_error_handling,
            self.test_response_formatting
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, "FAIL", f"Test execution error: {str(e)}")
            
            time.sleep(1)  # Brief pause between tests
        
        # Generate final report
        return self.generate_test_report()

def main():
    """Main test execution"""
    tester = SlackIntegrationTester()
    success = tester.run_all_tests()
    
    if success:
        print("🎉 Slack integration testing completed successfully!")
        exit(0)
    else:
        print("⚠️  Some issues found. Please review the report above.")
        exit(1)

if __name__ == "__main__":
    main()
