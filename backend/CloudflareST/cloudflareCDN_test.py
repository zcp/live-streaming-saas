import subprocess
import os
import time

# --- Configuration Area ---
# Path to the CloudflareST.exe program
EXECUTABLE_PATH = ".\\CloudflareST.exe"

# A dictionary of URLs to test, with a label for each
VIDEO_URLS = {
    "cdn": "https://lancet.im/videos/hls/playlist_local.m3u8",
    "r2": "https://pub-8ea55317b8624238a35e5c73454b9d2d.r2.dev/videos/hls/playlist_local.m3u8",
}

# !!! KEY SETTING: How long to let each test run before forcing it to stop (in seconds).
# Adjust this based on how long a normal test should take.
# Let's start with 5 minutes (300 seconds).
TEST_TIMEOUT_SECONDS = 240


# --- End of Configuration Area ---

def run_cloudflare_st(executable, label, url, timeout):
    """
    Calls CloudflareST.exe to test the specified URL and forces it to terminate
    if it runs longer than the specified timeout.
    """
    if not os.path.exists(executable):
        print(f"Error: Executable '{executable}' not found.")
        return

    save_file = f"result_{label}.csv"
    command = [executable, "-o", save_file, "-url", url]

    print("=" * 60)
    print(f"✅ STARTING test for label: '{label}' (Timeout set to {timeout} seconds)")
    print(f"   - Command: {' '.join(command)}")
    print("=" * 60)

    start_time = time.time()

    # Use Popen to run the process in a non-blocking way initially
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='ignore')

    try:
        # process.communicate() waits for the process to finish, but with a timeout.
        # It captures the full standard output and standard error.
        stdout, stderr = process.communicate(timeout=timeout)

        # If we reach here, the process finished on its own before the timeout
        print("--- Process finished on its own ---")
        print(stdout)
        if stderr:
            print("\n--- Program Error Output ---")
            print(stderr)

    except subprocess.TimeoutExpired:
        # This block runs if the process did not finish within the timeout
        print(f"\n⏳ Process did not complete in {timeout} seconds. Forcing termination (simulating Ctrl+C)...")

        # Forcefully terminate the process
        process.terminate()  # You can also use process.kill() for a more forceful stop

        # We can still get the output that was generated before the timeout
        stdout, stderr = process.communicate()
        print("--- Program Output (before termination) ---")
        print(stdout)
        print("✅ Process terminated successfully.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        process.kill()  # Kill the process in case of other errors

    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"Test for '{label}' concluded in {duration:.2f} seconds.")


if __name__ == "__main__":
    for label, url in VIDEO_URLS.items():
        run_cloudflare_st(EXECUTABLE_PATH, label, url, TEST_TIMEOUT_SECONDS)

    print("\n🎉 All tests are complete!")