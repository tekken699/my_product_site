# timer_utils.py
from time import perf_counter
from contextlib import contextmanager

@contextmanager
def timer(section_name: str):
    start = perf_counter()
    yield
    end = perf_counter()
    print(f"[TIMER] {section_name} took {end - start:.4f} seconds")
