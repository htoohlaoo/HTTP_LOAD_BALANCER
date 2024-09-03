import requests
import threading
import time
import argparse
from datetime import datetime

def send_requests(url, num_requests, results, thread_id):
    """
    Send a specified number of requests to a given URL and log the thread ID, timestamp, and response time.
    
    Args:
        url (str): The URL to send requests to.
        num_requests (int): The number of requests to send.
        results (list): A list to store the status code and other details of each request.
        thread_id (int): The ID of the thread sending the requests.
    """
    for _ in range(num_requests):
        start_time = time.time()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            response = requests.get(url)
            response_time = time.time() - start_time
            results.append((thread_id, timestamp, response.status_code, response_time))
            print(f"Thread {thread_id} - Timestamp: {timestamp} - Status Code: {response.status_code} - Response Time: {response_time:.4f} seconds")
        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            results.append((thread_id, timestamp, None, response_time))
            print(f"Thread {thread_id} - Timestamp: {timestamp} - Request failed: {e} - Response Time: {response_time:.4f} seconds")

def load_test(url, total_requests, concurrent_threads):
    """
    Perform a load test on a given URL.

    Args:
        url (str): The URL to load test.
        total_requests (int): Total number of requests to send.
        concurrent_threads (int): Number of concurrent threads to use for sending requests.
    """
    threads = []
    results = []
    requests_per_thread = total_requests // concurrent_threads

    # Start timing the test
    start_time = time.time()

    # Create and start threads
    for i in range(concurrent_threads):
        thread = threading.Thread(target=send_requests, args=(url, requests_per_thread, results, i))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # End timing the test
    end_time = time.time()

    # Calculate and print test statistics
    duration = end_time - start_time
    successful_requests = len([result for result in results if result[2] == 200])
    failed_requests = len([result for result in results if result[2] is None])
    print(f"\nTotal Requests: {total_requests}")
    print(f"Successful Requests: {successful_requests}")
    print(f"Failed Requests: {failed_requests}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Requests per Second: {total_requests / duration:.2f}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Simple Load Test Script',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--target_url', type=str, required=True, help='The target URL for the load test.\nExample: http://127.0.0.1:8080')
    parser.add_argument('--total_requests', type=int, required=True, help='Total number of requests to send.\nExample: 1000')
    parser.add_argument('--threads', type=int, required=True, help='Number of concurrent threads to use.\nExample: 10')
    
    # Parse the arguments
    args = parser.parse_args()

    # Start the load test with provided arguments
    load_test(args.target_url, args.total_requests, args.threads)
