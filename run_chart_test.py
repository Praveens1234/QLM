import traceback
from tests.test_chart_provider import test_chart_window_resampling, test_chart_cursor_pagination, mock_dataset_file
import pytest

# Manually run the two failing tests to see output
def run_tests():
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        file_path, df = mock_dataset_file(path)
        
        try:
            print("--- test_chart_window_resampling ---")
            test_chart_window_resampling((file_path, df))
            print("Passed!")
        except Exception as e:
            traceback.print_exc()

        try:
            print("--- test_chart_cursor_pagination ---")
            test_chart_cursor_pagination((file_path, df))
            print("Passed!")
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    run_tests()
