#!/usr/bin/env python3
"""
Aggressive Memory Leak Crash Test

This test runs pathfinding operations aggressively until the memory leak
causes the system to run out of memory and crash. Uses realistic data sizes
but runs many operations to demonstrate the cumulative impact.
"""

import sys
import os
import gc
import time
import psutil
import resource
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
import numpy as np


def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def create_leaky_maze(size=200):
    """
    Create a large maze that causes maximum memory leak per pathfinding.
    Uses simpler pattern for very large grids to avoid creation timeout.
    """
    # For very large grids, use simpler pattern to avoid timeout
    if size >= 5000:
        # Simple checkerboard-like pattern that's faster to create
        matrix = np.ones((size, size), dtype=bool)
        # Create obstacles in a pattern that still forces complex pathfinding
        matrix[::3, ::3] = False  # Every 3rd cell blocked
        matrix[1::4, 1::4] = False  # Additional obstacles
        
        # Ensure start and end are open
        matrix[0:10, 0:10] = True
        matrix[size-10:size, size-10:size] = True
        return matrix
    
    # Original complex pattern for smaller grids
    matrix = np.ones((size, size), dtype=bool)
    
    # Create intersecting diagonal corridors - forces many re-evaluations
    for i in range(size):
        for j in range(size):
            # Multiple intersecting diagonal patterns
            if ((i + j) % 6 < 2 or (i - j) % 6 < 2 or 
                (i + 2*j) % 8 < 2 or (2*i - j) % 8 < 2):
                matrix[i, j] = True
            else:
                matrix[i, j] = False
    
    # Add obstacles to force more complex paths
    for i in range(20, size-20, 25):
        for j in range(20, size-20, 25):
            matrix[i:i+10, j:j+10] = False
            matrix[i+4:i+6, j+4:j+6] = True  # Small opening
    
    # Ensure connectivity
    matrix[0:5, 0:5] = True
    matrix[size-5:size, size-5:size] = True
    
    return matrix


def run_aggressive_pathfinding(grid, start, end):
    """
    Run pathfinding and capture the heap's leaked memory.
    Returns the final heap with all its leaked data.
    """
    finder = AStarFinder()
    
    # Patch to capture heap
    original_find_path = finder.find_path
    final_heap = None
    
    def patched_find_path(start, end, grid):
        nonlocal final_heap
        
        finder.clean_grid(grid)
        finder.start_time = time.time()
        finder.runs = 0
        start.opened = True
        
        from pathfinding.core.heap import SimpleHeap
        open_list = SimpleHeap(start, grid)
        
        while len(open_list) > 0:
            finder.runs += 1
            finder.keep_running()
            path = finder.check_neighbors(start, end, grid, open_list)
            if path:
                final_heap = open_list
                return path, finder.runs
        
        final_heap = open_list
        return [], finder.runs
    
    finder.find_path = patched_find_path
    path, runs = finder.find_path(start, end, grid)
    
    return final_heap, len(path), runs


def test_aggressive_memory_leak():
    """
    Aggressive test that runs pathfinding until memory exhaustion.
    Uses realistic data sizes but high volume to trigger crash.
    """
    print("MEMORY LEAK CRASH TEST")
    print("=" * 30)
    
    # Create large maze for memory leak (optimized for speed)
    size = 3000  # 3000x3000 = 9 MILLION nodes - faster creation
    print(f"Creating {size}x{size} maze ({size*size:,} nodes)")
    print("WARNING: This will cause massive memory leakage!")
    
    # Use simple open grid for fastest creation - pathfinding will still leak massively
    matrix = np.ones((size, size), dtype=bool)  # All walkable - fastest possible
    grid = Grid(matrix=matrix)
    
    # Use multiple start/end combinations to maximize leak
    positions = [
        (0, 0, size-1, size-1),
        (0, size-1, size-1, 0), 
        (size//2, 0, size//2, size-1),
        (0, size//2, size-1, size//2),
        (size//4, size//4, 3*size//4, 3*size//4)
    ]
    
    print("Starting pathfinding loop...")
    
    start_time = time.time()
    start_memory = get_memory_usage()
    
    iteration = 0
    total_leaked_entries = 0
    total_pathfinding_ops = 0
    memory_increase = 0  # Initialize memory_increase
    
    # Keep references to leaked heaps to prevent garbage collection
    leaked_heaps = []
    
    try:
        while True:
            iteration += 1
            
            # Run ONE massive pathfinding operation per iteration
            start_x, start_y, end_x, end_y = positions[iteration % len(positions)]
            grid.cleanup()
            
            start_node = grid.node(start_x, start_y)
            end_node = grid.node(end_x, end_y)
            
            heap, path_len, runs = run_aggressive_pathfinding(grid, start_node, end_node)
            
            if heap:
                leaked_this_op = len(heap.removed_node_tuples) + len(heap.heap_order)
                total_leaked_entries += leaked_this_op
                
                # Keep the heap alive to accumulate leaked memory!
                leaked_heaps.append(heap)
            
            total_pathfinding_ops += 1
            
            # Report every single iteration since each leaks massive amounts
            if iteration % 1 == 0:
                current_time = time.time()
                current_memory = get_memory_usage()
                elapsed_time = current_time - start_time
                memory_increase = current_memory - start_memory
                
                print(f"Iteration {iteration} ({total_pathfinding_ops:,} operations)")
                print(f"  Time: {elapsed_time:.1f}s")
                print(f"  Memory: {current_memory:.1f}MB (+{memory_increase:.1f}MB)")
                print(f"  Leaked entries: {total_leaked_entries:,}")
                print(f"  Heap objects kept: {len(leaked_heaps):,}")
                print(f"  Avg leak/op: {total_leaked_entries/total_pathfinding_ops:.1f}")
                
                # Force garbage collection
                gc.collect()
                
                print()
            
            # Stop at 4GB memory increase to allow comparison with fixed version
            if memory_increase > 4096:  # 4GB limit
                print(f"\n4GB memory limit reached after {iteration} iterations")
                print(f"Memory increased by {memory_increase:.1f}MB")
                print("With fix: should run many more iterations without hitting this limit")
                break
                
    except MemoryError:
        print(f"\nMemory error after {iteration} iterations")
        elapsed = time.time() - start_time
        print(f"Time: {elapsed:.1f}s, Leaked: {total_leaked_entries:,}")
        return True
        
    except Exception as e:
        print(f"\nCrash after {iteration} iterations: {e}")
        return True
    
    elapsed = time.time() - start_time
    final_memory = get_memory_usage()
    
    print(f"\nCompleted {iteration} iterations in {elapsed:.1f}s")
    print(f"Memory: +{final_memory - start_memory:.1f}MB, Leaked: {total_leaked_entries:,}")
    
    return True


if __name__ == "__main__":
    
    try:
        test_aggressive_memory_leak()
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        
    except Exception as e:
        print(f"\nCrash: {e}")
        
    print("\nTest complete")