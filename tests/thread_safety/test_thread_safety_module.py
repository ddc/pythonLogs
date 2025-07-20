"""Comprehensive tests for thread_safety.py module."""
import threading
import time
from typing import List
import pytest
from pythonLogs.thread_safety import (
    ThreadSafeMeta,
    thread_safe,
    auto_thread_safe,
    AutoThreadSafe,
    synchronized_method,
    ThreadSafeContext
)


class TestThreadSafeDecorator:
    """Test the @thread_safe decorator."""

    def test_thread_safe_decorator_basic(self):
        """Test basic functionality of @thread_safe decorator."""
        
        class TestClass:
            def __init__(self):
                self._lock = threading.RLock()
                self.counter = 0
            
            @thread_safe
            def increment(self):
                current = self.counter
                time.sleep(0.001)  # Simulate some work
                self.counter = current + 1
        
        threads = []
        
        def worker():
            for _ in range(10):
                obj.increment()
        
        obj = TestClass()
        
        # Create multiple threads
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should be exactly 50 (5 threads * 10 increments each)
        assert obj.counter == 50, f"Expected 50, got {obj.counter}"

    def test_thread_safe_decorator_without_lock(self):
        """Test @thread_safe decorator uses class lock when no instance lock exists."""
        
        class TestClass:
            def __init__(self):
                self.counter = 0
            
            @thread_safe
            def increment(self):
                self.counter += 1
        
        obj = TestClass()
        # Should fall back to creating a class-level lock in the decorator
        obj.increment()
        assert obj.counter == 1
        
        # The lock should be accessible via the method's fallback mechanism
        lock = getattr(obj, '_lock', None) or getattr(obj.__class__, '_lock', None)
        assert lock is not None

    def test_thread_safe_decorator_preserves_metadata(self):
        """Test that @thread_safe preserves function metadata."""
        
        class TestClass:
            def __init__(self):
                self._lock = threading.RLock()
            
            @thread_safe
            def test_method(self, arg1, arg2=None):
                """Test method docstring."""
                return f"{arg1}-{arg2}"
        
        obj = TestClass()
        method = obj.test_method
        
        # Check that wrapper preserves original function name and docstring
        assert method.__name__ == 'test_method'
        assert 'Test method docstring' in method.__doc__
        assert method(1, arg2=2) == "1-2"


class TestAutoThreadSafeDecorator:
    """Test the @auto_thread_safe decorator."""

    def test_auto_thread_safe_specific_methods(self):
        """Test @auto_thread_safe with specific method list."""
        
        @auto_thread_safe(['increment'])
        class TestClass:
            def __init__(self):
                self.counter = 0
            
            def increment(self):
                current = self.counter
                time.sleep(0.001)
                self.counter = current + 1
            
            def unsafe_increment(self):
                self.counter += 1
        
        obj = TestClass()
        
        # Check that specified method is wrapped
        assert hasattr(obj.increment, '_thread_safe_wrapped')
        # Check that non-specified method is not wrapped
        assert not hasattr(obj.unsafe_increment, '_thread_safe_wrapped')
        
        # Test thread safety of wrapped method
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=obj.increment)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert obj.counter == 10

    def test_auto_thread_safe_all_public_methods(self):
        """Test @auto_thread_safe without method list wraps all public methods."""
        
        @auto_thread_safe()
        class TestClass:
            def __init__(self):
                self.counter = 0
            
            def increment(self):
                self.counter += 1
            
            def decrement(self):
                self.counter -= 1
            
            def _private_method(self):
                pass
        
        obj = TestClass()
        
        # Public methods should be wrapped
        assert hasattr(obj.increment, '_thread_safe_wrapped')
        assert hasattr(obj.decrement, '_thread_safe_wrapped')
        # Private method should not be wrapped
        assert not hasattr(obj._private_method, '_thread_safe_wrapped')

    def test_auto_thread_safe_no_double_wrapping(self):
        """Test that methods are not wrapped multiple times."""
        
        @auto_thread_safe(['test_method'])
        class TestClass:
            def test_method(self):
                return "test"
        
        obj = TestClass()
        
        # Apply decorator again (should not double-wrap)
        test_class = auto_thread_safe(['test_method'])(TestClass)
        obj2 = test_class()
        
        # Should still work and not be double-wrapped
        assert obj2.test_method() == "test"


class TestThreadSafeMeta:
    """Test the ThreadSafeMeta metaclass."""

    def test_thread_safe_meta_basic(self):
        """Test basic ThreadSafeMeta functionality."""
        
        class TestClass(metaclass=ThreadSafeMeta):
            _thread_safe_methods = ['increment']
            
            def __init__(self):
                self.counter = 0
            
            def increment(self):
                current = self.counter
                time.sleep(0.001)
                self.counter = current + 1
            
            def unsafe_method(self):
                pass
        
        obj = TestClass()
        
        # Should have class-level lock
        assert hasattr(obj.__class__, '_lock')
        # Test that increment method works
        obj.increment()
        assert obj.counter == 1

    def test_thread_safe_meta_auto_detection(self):
        """Test ThreadSafeMeta auto-detects public methods."""
        
        class TestClass(metaclass=ThreadSafeMeta):
            def __init__(self):
                self.value = 0
            
            def public_method(self):
                return "public"
            
            def _private_method(self):
                return "private"
        
        obj = TestClass()
        
        # Should have class-level lock
        assert hasattr(obj.__class__, '_lock')
        # Test that methods work
        assert obj.public_method() == "public"
        assert obj._private_method() == "private"


class TestAutoThreadSafeBaseClass:
    """Test the AutoThreadSafe base class."""

    def test_auto_thread_safe_base_class(self):
        """Test AutoThreadSafe base class functionality."""
        
        class TestClass(AutoThreadSafe):
            def __init__(self):
                super().__init__()
                self.counter = 0
            
            def increment(self):
                current = self.counter
                time.sleep(0.001)
                self.counter = current + 1
        
        obj = TestClass()
        
        # Should have instance lock
        assert hasattr(obj, '_lock')
        # Public method should be wrapped
        assert hasattr(obj.increment, '_thread_safe_wrapped')
        
        # Test thread safety
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=obj.increment)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert obj.counter == 10

    def test_auto_thread_safe_inheritance(self):
        """Test AutoThreadSafe with inheritance."""
        
        class BaseClass(AutoThreadSafe):
            def __init__(self):
                super().__init__()
                self.value = 0
            
            def base_method(self):
                self.value += 1
        
        class DerivedClass(BaseClass):
            def __init__(self):
                super().__init__()
                self.derived_value = 0
            
            def derived_method(self):
                self.derived_value += 1
        
        obj = DerivedClass()
        
        # Both base and derived methods should be thread-safe
        assert hasattr(obj.base_method, '_thread_safe_wrapped')
        assert hasattr(obj.derived_method, '_thread_safe_wrapped')


class TestSynchronizedMethodDecorator:
    """Test the @synchronized_method decorator."""

    def test_synchronized_method_decorator(self):
        """Test @synchronized_method decorator."""
        
        class TestClass:
            def __init__(self):
                self._lock = threading.RLock()
                self.counter = 0
            
            @synchronized_method
            def increment(self):
                current = self.counter
                time.sleep(0.001)
                self.counter = current + 1
        
        obj = TestClass()
        
        # Test thread safety
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=obj.increment)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert obj.counter == 10


class TestThreadSafeContext:
    """Test the ThreadSafeContext context manager."""

    def test_thread_safe_context_manager(self):
        """Test ThreadSafeContext context manager."""
        lock = threading.RLock()
        counter = [0]  # Use list to make it mutable
        
        def worker():
            with ThreadSafeContext(lock):
                current = counter[0]
                time.sleep(0.001)
                counter[0] = current + 1
        
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert counter[0] == 10

    def test_thread_safe_context_exception_handling(self):
        """Test ThreadSafeContext properly releases lock on exception."""
        lock = threading.RLock()
        
        try:
            with ThreadSafeContext(lock):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Lock should be released even after exception
        assert lock.acquire(blocking=False)
        lock.release()


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_thread_safe_with_static_methods(self):
        """Test thread safety with static methods."""
        
        @auto_thread_safe(['regular_method'])
        class TestClass:
            counter = 0
            
            def regular_method(self):
                TestClass.counter += 1
            
            @staticmethod
            def static_method():
                return "static"
        
        obj = TestClass()
        
        # Regular method should be wrapped
        assert hasattr(obj.regular_method, '_thread_safe_wrapped')
        # Static method should not be affected
        assert TestClass.static_method() == "static"

    def test_thread_safe_with_class_methods(self):
        """Test thread safety with class methods."""
        
        @auto_thread_safe(['regular_method'])
        class TestClass:
            counter = 0
            
            def regular_method(self):
                self.__class__.counter += 1
            
            @classmethod
            def class_method(cls):
                return "class"
        
        obj = TestClass()
        
        # Regular method should be wrapped
        assert hasattr(obj.regular_method, '_thread_safe_wrapped')
        # Class method should work normally
        assert TestClass.class_method() == "class"

    def test_thread_safe_with_properties(self):
        """Test thread safety with properties."""
        
        @auto_thread_safe(['set_value'])
        class TestClass:
            def __init__(self):
                self._value = 0
            
            @property
            def value(self):
                return self._value
            
            def set_value(self, val):
                self._value = val
        
        obj = TestClass()
        
        # Property should work normally
        assert obj.value == 0
        obj.set_value(42)
        assert obj.value == 42

    def test_multiple_decorator_applications(self):
        """Test applying decorators multiple times."""
        
        class TestClass:
            def __init__(self):
                self._lock = threading.RLock()
                self.counter = 0
            
            def increment(self):
                self.counter += 1
        
        # Apply auto_thread_safe multiple times
        test_class = auto_thread_safe(['increment'])(TestClass)
        test_class = auto_thread_safe(['increment'])(test_class)
        
        obj = test_class()
        obj.increment()
        assert obj.counter == 1

    def test_thread_safety_with_exceptions(self):
        """Test that locks are properly released when exceptions occur."""
        
        class TestClass:
            def __init__(self):
                self._lock = threading.RLock()
                self.counter = 0
            
            @thread_safe
            def failing_method(self):
                self.counter += 1
                raise ValueError("Test exception")
        
        obj = TestClass()
        
        # Method should raise exception but lock should be released
        with pytest.raises(ValueError):
            obj.failing_method()
        
        # Lock should be available for next call
        assert obj._lock.acquire(blocking=False)
        obj._lock.release()
        
        assert obj.counter == 1

    def test_nested_thread_safe_calls(self):
        """Test nested calls to thread-safe methods."""
        
        class TestClass:
            def __init__(self):
                self._lock = threading.RLock()
                self.counter = 0
            
            @thread_safe
            def outer_method(self):
                self.counter += 1
                self.inner_method()
            
            @thread_safe
            def inner_method(self):
                self.counter += 10
        
        obj = TestClass()
        obj.outer_method()
        
        # Should work with nested calls (RLock allows reentrance)
        assert obj.counter == 11