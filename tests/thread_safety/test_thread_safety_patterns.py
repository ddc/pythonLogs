"""Test different thread safety usage patterns and advanced scenarios."""

import gc
import threading
import time
import weakref
from concurrent.futures import as_completed, ThreadPoolExecutor


class TestAdvancedThreadSafetyPatterns:
    """Test advanced thread safety patterns and real-world scenarios."""

    def test_producer_consumer_pattern(self):
        """Test thread safety in producer-consumer pattern."""

        class ThreadSafeQueue:
            def __init__(self, maxsize=10):
                self.queue = []
                self.maxsize = maxsize
                self.condition = threading.Condition()

            def put(self, item):
                with self.condition:
                    while len(self.queue) >= self.maxsize:
                        self.condition.wait()
                    self.queue.append(item)
                    self.condition.notify_all()

            def get(self):
                with self.condition:
                    while not self.queue:
                        self.condition.wait()
                    item = self.queue.pop(0)
                    self.condition.notify_all()
                    return item

            def size(self):
                with self.condition:
                    return len(self.queue)

        queue = ThreadSafeQueue(maxsize=5)
        results = []

        def producer(start, end):
            for i in range(start, end):
                queue.put(f"item_{i}")
                time.sleep(0.001)

        def consumer(count):
            items = []
            for _ in range(count):
                item = queue.get()
                items.append(item)
                time.sleep(0.001)
            results.extend(items)

        # Start producers and consumers
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Start consumers first to ensure they're waiting
            consumer_futures = [executor.submit(consumer, 10), executor.submit(consumer, 10)]

            # Small delay to let consumers start waiting
            time.sleep(0.01)

            # Start producers
            producer_futures = [executor.submit(producer, 0, 10), executor.submit(producer, 10, 20)]

            # Wait for completion
            for future in as_completed(producer_futures + consumer_futures):
                future.result()

        # Should have consumed all 20 items
        assert len(results) == 20
        assert queue.size() == 0

    def test_reader_writer_pattern(self):
        """Test thread safety in reader-writer pattern."""

        class ThreadSafeDataStore:
            def __init__(self):
                self.data = {}
                self.read_count = 0
                self.write_count = 0
                self._lock = threading.RLock()

            def read(self, key):
                with self._lock:
                    self.read_count += 1
                    time.sleep(0.001)  # Simulate read time
                    return self.data.get(key)

            def write(self, key, value):
                with self._lock:
                    self.write_count += 1
                    time.sleep(0.001)  # Simulate write time
                    self.data[key] = value

            def get_stats(self):
                with self._lock:
                    return {'reads': self.read_count, 'writes': self.write_count, 'data_size': len(self.data)}

        store = ThreadSafeDataStore()

        def writer(start, end):
            for i in range(start, end):
                store.write(f"key_{i}", f"value_{i}")

        def reader(keys):
            results = []
            for key in keys:
                value = store.read(key)
                if value:
                    results.append((key, value))
            return results

        # Start writers first
        with ThreadPoolExecutor(max_workers=8) as executor:
            writer_futures = [executor.submit(writer, 0, 25), executor.submit(writer, 25, 50)]

            # Wait for some writes to complete
            time.sleep(0.1)

            # Start readers
            reader_futures = [
                executor.submit(reader, [f"key_{i}" for i in range(0, 20)]),
                executor.submit(reader, [f"key_{i}" for i in range(20, 40)]),
                executor.submit(reader, [f"key_{i}" for i in range(30, 50)]),
            ]

            # Collect results
            for future in as_completed(writer_futures + reader_futures):
                future.result()

        stats = store.get_stats()
        assert stats['writes'] == 50
        assert stats['data_size'] == 50
        assert stats['reads'] > 0  # Some reads should have occurred

    def test_singleton_pattern_thread_safety(self):
        """Test thread-safe singleton pattern."""

        class ThreadSafeSingleton:
            _instance = None
            _instance_lock = threading.RLock()

            def __init__(self):
                if ThreadSafeSingleton._instance is not None:
                    raise RuntimeError("Use get_instance() to get singleton")
                self.created_at = time.time()
                self.counter = 0

            @classmethod
            def get_instance(cls):
                if cls._instance is None:
                    with cls._instance_lock:
                        if cls._instance is None:
                            cls._instance = cls()
                return cls._instance

            def increment(self):
                with self._instance_lock:
                    self.counter += 1

        instances = []

        def get_singleton():
            instance = ThreadSafeSingleton.get_instance()
            instances.append(instance)
            instance.increment()
            return instance

        # Create multiple threads trying to get singleton
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_singleton) for _ in range(50)]
            results = [future.result() for future in as_completed(futures)]

        # All instances should be the same object
        assert len({id(inst) for inst in instances}) == 1
        # The Counter should be exactly 50
        assert instances[0].counter == 50

    def test_resource_pool_pattern(self):
        """Test thread-safe resource pool pattern."""

        class ThreadSafeResourcePool:
            def __init__(self, create_resource_func, pool_size=5):
                self.create_resource = create_resource_func
                self.pool_size = pool_size
                self.available = []
                self.in_use = set()
                self.condition = threading.Condition()
                self._lock = threading.RLock()

                # Pre-populate pool
                for _ in range(pool_size):
                    self.available.append(self.create_resource())

            def get_resource(self, timeout=None):
                with self.condition:
                    start_time = time.time()
                    while not self.available:
                        if timeout and (time.time() - start_time) > timeout:
                            raise TimeoutError("No resource available")
                        self.condition.wait(timeout=0.1)

                    resource = self.available.pop()
                    self.in_use.add(resource)
                    return resource

            def return_resource(self, resource):
                with self.condition:
                    if resource in self.in_use:
                        self.in_use.remove(resource)
                        self.available.append(resource)
                        self.condition.notify()

            def stats(self):
                with self._lock:
                    return {
                        'available': len(self.available),
                        'in_use': len(self.in_use),
                        'total': len(self.available) + len(self.in_use),
                    }

        # Create a simple resource (just a counter)
        resource_counter = [0]

        def create_resource():
            resource_counter[0] += 1
            return f"resource_{resource_counter[0]}"

        pool = ThreadSafeResourcePool(create_resource, pool_size=3)
        completed_tasks = []

        def worker(worker_id):
            try:
                resource = pool.get_resource(timeout=1.0)
                time.sleep(0.1)  # Simulate work
                completed_tasks.append(f"worker_{worker_id}_used_{resource}")
                pool.return_resource(resource)
            except TimeoutError:
                completed_tasks.append(f"worker_{worker_id}_timeout")

        # Start more workers than available resources
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(8)]
            for future in as_completed(futures):
                future.result()

        stats = pool.stats()
        assert stats['total'] == 3  # Pool size maintained
        assert stats['available'] == 3  # All resources returned
        assert stats['in_use'] == 0  # No resources stuck
        assert len(completed_tasks) == 8  # All workers completed

    def test_cache_with_expiry_thread_safety(self):
        """Test thread-safe cache with expiry."""

        class ThreadSafeExpiryCache:
            def __init__(self, default_ttl=1.0):
                self.cache = {}
                self.timestamps = {}
                self.default_ttl = default_ttl
                self._lock = threading.RLock()

            def get(self, key):
                with self._lock:
                    if key in self.cache:
                        if time.time() - self.timestamps[key] < self.default_ttl:
                            return self.cache[key]
                        else:
                            # Expired
                            del self.cache[key]
                            del self.timestamps[key]
                    return None

            def put(self, key, value, ttl=None):
                with self._lock:
                    self.cache[key] = value
                    self.timestamps[key] = time.time()

            def cleanup(self):
                with self._lock:
                    current_time = time.time()
                    expired_keys = [
                        key
                        for key, timestamp in self.timestamps.items()
                        if current_time - timestamp >= self.default_ttl
                    ]
                    for key in expired_keys:
                        del self.cache[key]
                        del self.timestamps[key]
                    return len(expired_keys)

            def size(self):
                with self._lock:
                    return len(self.cache)

        cache = ThreadSafeExpiryCache(default_ttl=0.1)

        def cache_worker(worker_id):
            # Put some data
            for i in range(5):
                cache.put(f"key_{worker_id}_{i}", f"value_{worker_id}_{i}")

            # Try to get data immediately
            results = []
            for i in range(5):
                value = cache.get(f"key_{worker_id}_{i}")
                if value:
                    results.append(value)

            return results

        # Run workers concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cache_worker, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # Wait for expiry
        time.sleep(0.2)

        # Cleanup expired entries
        expired_count = cache.cleanup()

        # Most entries should have expired
        assert expired_count > 0
        assert cache.size() < 25  # Should be less than total inserted

    def test_event_bus_thread_safety(self):
        """Test thread-safe event bus pattern."""

        class ThreadSafeEventBus:
            def __init__(self):
                self.subscribers = {}
                self.event_count = {}
                self._lock = threading.RLock()

            def subscribe(self, event_type, callback):
                with self._lock:
                    if event_type not in self.subscribers:
                        self.subscribers[event_type] = []
                    self.subscribers[event_type].append(callback)

            def unsubscribe(self, event_type, callback):
                with self._lock:
                    if event_type in self.subscribers:
                        try:
                            self.subscribers[event_type].remove(callback)
                        except ValueError:
                            pass

            def publish(self, event_type, data):
                with self._lock:
                    self.event_count[event_type] = self.event_count.get(event_type, 0) + 1
                    if event_type in self.subscribers:
                        for callback in self.subscribers[event_type][:]:  # Copy to avoid modification during iteration
                            try:
                                callback(data)
                            except Exception:
                                pass  # Ignore callback errors

            def get_stats(self):
                with self._lock:
                    return {
                        'subscriber_count': sum(len(subs) for subs in self.subscribers.values()),
                        'event_types': len(self.subscribers),
                        'events_published': dict(self.event_count),
                    }

        event_bus = ThreadSafeEventBus()
        received_events = []
        events_lock = threading.RLock()

        def event_handler(event_type):
            def handler(data):
                with events_lock:
                    received_events.append((event_type, data))

            return handler

        def publisher(event_type, count):
            for i in range(count):
                event_bus.publish(event_type, f"{event_type}_data_{i}")
                time.sleep(0.001)

        def subscriber(event_type):
            handler = event_handler(event_type)
            event_bus.subscribe(event_type, handler)
            time.sleep(0.05)  # Let some events be published
            return handler

        # Start subscribers and publishers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Start subscribers
            sub_futures = [
                executor.submit(subscriber, "type_A"),
                executor.submit(subscriber, "type_B"),
                executor.submit(subscriber, "type_A"),  # Multiple subscribers the same type
            ]

            # Start publishers
            pub_futures = [
                executor.submit(publisher, "type_A", 10),
                executor.submit(publisher, "type_B", 5),
                executor.submit(publisher, "type_C", 3),  # No subscribers
            ]

            # Wait for completion
            for future in as_completed(sub_futures + pub_futures):
                future.result()

        stats = event_bus.get_stats()

        # Should have received events for subscribed types
        type_a_events = [e for e in received_events if e[0] == "type_A"]
        type_b_events = [e for e in received_events if e[0] == "type_B"]

        assert len(type_a_events) > 0  # type_A had 2 subscribers
        assert len(type_b_events) > 0  # type_B had 1 subscriber
        assert stats['events_published']['type_A'] == 10
        assert stats['events_published']['type_B'] == 5
        assert stats['events_published']['type_C'] == 3

    def test_weak_reference_cleanup_thread_safety(self):
        """Test thread safety with weak references and cleanup."""

        class ThreadSafeWeakRegistry:
            def __init__(self):
                self.registry = {}
                self.cleanup_count = 0
                self._lock = threading.RLock()

            def register(self, obj, name):
                def cleanup_callback(weak_ref):
                    with self._lock:
                        self.cleanup_count += 1
                        if name in self.registry:
                            del self.registry[name]

                with self._lock:
                    weak_ref = weakref.ref(obj, cleanup_callback)
                    self.registry[name] = weak_ref

            def cleanup(self):
                with self._lock:
                    # Manual cleanup of dead references
                    dead_refs = []
                    for name, weak_ref in self.registry.items():
                        if weak_ref() is None:
                            dead_refs.append(name)

                    for name in dead_refs:
                        del self.registry[name]

                    return len(dead_refs)

            def get_count(self):
                with self._lock:
                    return len(self.registry)

            def get_cleanup_count(self):
                with self._lock:
                    return self.cleanup_count

        registry = ThreadSafeWeakRegistry()

        def create_and_register_objects(start, end):
            objects = []
            for i in range(start, end):
                # Create a proper object that can have weak references
                obj = type(f"TestObject_{i}", (), {"value": i})()
                registry.register(obj, f"name_{i}")
                objects.append(obj)

            # Let some objects go out of scope gradually
            for i in range(len(objects)):
                if i % 2 == 0:
                    objects[i] = None  # Clear reference
                time.sleep(0.001)

            return len([obj for obj in objects if obj is not None])

        # Create objects in multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_and_register_objects, i * 10, (i + 1) * 10) for i in range(5)]

            for future in as_completed(futures):
                future.result()

        # Force garbage collection
        gc.collect()
        time.sleep(0.1)

        # Manual cleanup
        cleaned = registry.cleanup()

        # Some cleanup should have occurred
        final_count = registry.get_count()
        cleanup_count = registry.get_cleanup_count()

        assert final_count < 50  # Some objects should be cleaned up
        assert cleanup_count >= 0  # Some automatic cleanup may have occurred
