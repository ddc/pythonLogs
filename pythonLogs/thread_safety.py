import functools
import threading
from typing import Any, Callable, Dict, Type, TypeVar


F = TypeVar('F', bound=Callable[..., Any])


class ThreadSafeMeta(type):
    """Metaclass that automatically adds thread safety to class methods."""

    def __new__(mcs, name: str, bases: tuple, namespace: Dict[str, Any], **kwargs):
        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace)

        # Add a class-level lock if not already present
        if not hasattr(cls, '_lock'):
            cls._lock = threading.RLock()

        # Get methods that should be thread-safe (exclude private/dunder methods)
        thread_safe_methods = getattr(cls, '_thread_safe_methods', None)
        if thread_safe_methods is None:
            # Auto-detect public methods that modify state
            thread_safe_methods = [
                method_name
                for method_name in namespace
                if (
                    callable(getattr(cls, method_name, None))
                    and not method_name.startswith('_')
                    and method_name not in ['__enter__', '__exit__', '__init__']
                )
            ]

        # Wrap each method with automatic locking
        for method_name in thread_safe_methods:
            if hasattr(cls, method_name):
                original_method = getattr(cls, method_name)
                if callable(original_method):
                    wrapped_method = thread_safe(original_method)
                    setattr(cls, method_name, wrapped_method)

        return cls


def thread_safe(func: F) -> F:
    """Decorator that automatically adds thread safety to methods."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Use instance lock if available, otherwise class lock
        lock = getattr(self, '_lock', None)
        if lock is None:
            # Check if class has lock, if not create one
            if not hasattr(self.__class__, '_lock'):
                self.__class__._lock = threading.RLock()
            lock = self.__class__._lock

        with lock:
            return func(self, *args, **kwargs)

    return wrapper


def _get_wrappable_methods(cls: Type) -> list:
    """Helper function to get methods that should be made thread-safe."""
    return [
        method_name
        for method_name in dir(cls)
        if (
            callable(getattr(cls, method_name, None))
            and not method_name.startswith('_')
            and method_name not in ['__enter__', '__exit__', '__init__']
        )
    ]


def _ensure_class_has_lock(cls: Type) -> None:
    """Ensure the class has a lock attribute."""
    if not hasattr(cls, '_lock'):
        cls._lock = threading.RLock()


def _should_wrap_method(cls: Type, method_name: str, original_method: Any) -> bool:
    """Check if a method should be wrapped with thread safety."""
    return (
        hasattr(cls, method_name) and callable(original_method) and not hasattr(original_method, '_thread_safe_wrapped')
    )


def auto_thread_safe(thread_safe_methods: list = None):
    """Class decorator that adds automatic thread safety to specified methods."""

    def decorator(cls: Type) -> Type:
        _ensure_class_has_lock(cls)

        # Store thread-safe methods list
        if thread_safe_methods:
            cls._thread_safe_methods = thread_safe_methods

        # Get methods to make thread-safe
        methods_to_wrap = thread_safe_methods or _get_wrappable_methods(cls)

        # Wrap each method
        for method_name in methods_to_wrap:
            original_method = getattr(cls, method_name, None)
            if _should_wrap_method(cls, method_name, original_method):
                wrapped_method = thread_safe(original_method)
                wrapped_method._thread_safe_wrapped = True
                setattr(cls, method_name, wrapped_method)

        return cls

    return decorator


class AutoThreadSafe:
    """Base class that provides automatic thread safety for all public methods."""

    def __init__(self):
        if not hasattr(self, '_lock'):
            self._lock = threading.RLock()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Add class-level lock
        if not hasattr(cls, '_lock'):
            cls._lock = threading.RLock()

        # Auto-wrap public methods
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr = getattr(cls, attr_name)
                if callable(attr) and not hasattr(attr, '_thread_safe_wrapped'):
                    wrapped_attr = thread_safe(attr)
                    wrapped_attr._thread_safe_wrapped = True
                    setattr(cls, attr_name, wrapped_attr)


def synchronized_method(func: F) -> F:
    """Decorator for individual methods that need thread safety."""
    return thread_safe(func)


class ThreadSafeContext:
    """Context manager for thread-safe operations."""

    def __init__(self, lock: threading.Lock):
        self.lock = lock

    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
