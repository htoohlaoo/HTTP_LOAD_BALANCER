import requests
import threading
import time
import argparse
from datetime import datetime

class LoadTestResult:
    """
    Represents the result of a single request sent during the load test.
    """

    def __init__(self, thread_id, timestamp, status_code, response_time):
        self.thread_id = thread_id
        self.timestamp = timestamp
        self.status_code = status_code
        self.response_time = response_time

def send_requests(url, num_requests, results, thread_id, inject_sql=False):
    """
    Sends a specified number of requests to a given URL, optionally injecting SQL if enabled.

    Args:
        url (str): The URL to send requests to.
        num_requests (int): The number of requests to send.
        results (list): A list to store the LoadTestResult objects for each request.
        thread_id (int): The ID of the thread sending the requests.
        inject_sql (bool, optional): Flag to enable or disable SQL injection.
    """

    for _ in range(num_requests):
        start_time = time.time()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            payload = ""
            if inject_sql:
                # **Disclaimer:** This simulates harmless SQL injection (e.g., comments)
                # for educational purposes only.
                payload= "' OR 1=1 --"  # Add a simple SQL injection payload

            response = requests.get(url,payload)
            response_time = time.time() - start_time
            results.append(LoadTestResult(thread_id, timestamp, response.status_code, response_time))
            print(f"Thread {thread_id} - Timestamp: {timestamp} - Status Code: {response.status_code} - Response Time: {response_time:.4f} seconds")
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            results.append(LoadTestResult(thread_id, timestamp, None, response_time))
            print(f"Thread {thread_id} - Timestamp: {timestamp} - Request failed: {e} - Response Time: {response_time:.4f} seconds")

def load_test(url, total_requests, concurrent_threads, inject_sql=False):
    """
    Performs a load test on a given URL using multiple threads, optionally injecting SQL if enabled.

    Args:
        url (str): The URL to load test.
        total_requests (int): Total number of requests to send.
        concurrent_threads (int): Number of concurrent threads to use for sending requests.
        inject_sql (bool, optional): Flag to enable or disable SQL injection.

    Returns:
        A dictionary containing load test statistics.
    """

    threads = []
    results = []
    requests_per_thread = total_requests // concurrent_threads

    # Start timing the test
    start_time = time.time()

    # Create and start threads
    for i in range(concurrent_threads):
        thread = threading.Thread(target=send_requests, args=(url, requests_per_thread, results, i, inject_sql))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # End timing the test
    end_time = time.time()

    # Calculate and print test statistics
    duration = end_time - start_time
    successful_requests = len([result for result in results if result.status_code == 200])
    failed_requests = len([result for result in results if result.status_code is None or result.status_code == 403])

    print(f"\nTotal Requests: {total_requests}")
    print(f"Successful Requests: {successful_requests}")
    print(f"Failed Requests: {failed_requests}")
    print(f"Duration: 1  {duration:.2f} seconds")
    print(f"Requests per Second: {total_requests / duration:.2f}")

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "duration": duration,
        "requests_per_second": total_requests / duration,
    }

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Professional Load Test Script with SQL Injection Options',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--target_url', type=str, required=True, help='The target URL for the load test.\nExample: http://127.0.0.1:8080')
    parser.add_argument('--total_requests', type=int, required=True, help='Total number of requests to send.\nExample: 1000')
    parser.add_argument('--threads', type=int, required=True, help='Number of concurrent threads to use.\nExample: 10')
    parser.add_argument('--inject_sql', action='store_true', help='Enable SQL injection simulation')

    # Parse the arguments
    args = parser.parse_args()

    load_test(args.target_url, args.total_requests, args.threads, args.inject_sql)