import time

class APILimiter:
    def __init__(self, max_calls_per_minute=12):
        self.max_calls = max_calls_per_minute
        self.call_times = []

    def wait_if_needed(self):
        """
        Checks how many calls were made in the last 60 seconds.
        If we hit the limit, it automatically pauses the code to stay safe.
        """
        current_time = time.time()
        
        # 1. Forget any API calls that happened more than 60 seconds ago
        self.call_times = [t for t in self.call_times if current_time - t < 60.0]
        
        # 2. If we are at our cap of 12, figure out how long to wait
        if len(self.call_times) >= self.max_calls:
            # Calculate how many seconds until the oldest API call "expires"
            wait_time = 60.0 - (current_time - self.call_times[0])
            
            if wait_time > 0:
                print(f"⏳ Security Limit Activated: Pausing for {round(wait_time, 1)} seconds to prevent API overload...")
                time.sleep(wait_time)
            
            # After waiting, manually remove that oldest call from our memory
            self.call_times = self.call_times[1:]
        
        # 3. Log the exact time of this new API call
        self.call_times.append(time.time())

# Create a global instance capped at 12 requests per minute
gemini_limiter = APILimiter(max_calls_per_minute=12)