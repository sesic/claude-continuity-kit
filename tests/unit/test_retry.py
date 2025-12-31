"""Tests for the retry decorator."""

import asyncio
import logging
import time

import pytest

from src.utils.retry import retry


class TestSyncRetrySuccessFirstTry:
    """Test sync functions that succeed on first try."""

    def test_sync_function_succeeds_first_try(self) -> None:
        call_count = 0

        @retry()
        def succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeeds()
        assert result == "success"
        assert call_count == 1

    def test_function_with_args_succeeds(self) -> None:
        @retry()
        def add(a: int, b: int) -> int:
            return a + b

        assert add(2, 3) == 5

    def test_function_with_kwargs_succeeds(self) -> None:
        @retry()
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        assert greet("World", greeting="Hi") == "Hi, World!"


class TestAsyncRetrySuccessFirstTry:
    """Test async functions that succeed on first try."""

    @pytest.mark.asyncio
    async def test_async_function_succeeds_first_try(self) -> None:
        call_count = 0

        @retry()
        async def async_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "async success"

        result = await async_succeeds()
        assert result == "async success"
        assert call_count == 1


class TestSyncRetryFailsThenSucceeds:
    """Test sync functions that fail initially then succeed."""

    def test_sync_function_fails_twice_then_succeeds(self) -> None:
        call_count = 0

        @retry(max_attempts=3)
        def fails_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        result = fails_twice()
        assert result == "success"
        assert call_count == 3

    def test_succeeds_on_last_attempt(self) -> None:
        call_count = 0

        @retry(max_attempts=3)
        def succeeds_last() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Not yet")
            return "finally"

        result = succeeds_last()
        assert result == "finally"
        assert call_count == 3


class TestAsyncRetryFailsThenSucceeds:
    """Test async functions that fail initially then succeed."""

    @pytest.mark.asyncio
    async def test_async_function_fails_twice_then_succeeds(self) -> None:
        call_count = 0

        @retry(max_attempts=3)
        async def async_fails_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "async success"

        result = await async_fails_twice()
        assert result == "async success"
        assert call_count == 3


class TestRetryExhaustion:
    """Test behavior when all retries are exhausted."""

    def test_sync_function_always_fails(self) -> None:
        call_count = 0

        @retry(max_attempts=3)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure #{call_count}")

        with pytest.raises(ValueError, match="Failure #3"):
            always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_function_always_fails(self) -> None:
        call_count = 0

        @retry(max_attempts=3)
        async def async_always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Async failure #{call_count}")

        with pytest.raises(ValueError, match="Async failure #3"):
            await async_always_fails()

        assert call_count == 3

    def test_single_attempt_raises_immediately(self) -> None:
        call_count = 0

        @retry(max_attempts=1)
        def single_attempt() -> str:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Single failure")

        with pytest.raises(RuntimeError, match="Single failure"):
            single_attempt()

        assert call_count == 1


class TestRetryDelay:
    """Test that delay is respected between retries."""

    def test_sync_delay_between_retries(self) -> None:
        call_count = 0
        call_times: list[float] = []

        @retry(max_attempts=3, delay=0.1)
        def timed_fails() -> str:
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 3:
                raise ValueError("Not yet")
            return "done"

        timed_fails()

        assert len(call_times) == 3
        assert call_times[1] - call_times[0] >= 0.09
        assert call_times[2] - call_times[1] >= 0.09

    @pytest.mark.asyncio
    async def test_async_delay_between_retries(self) -> None:
        call_count = 0
        call_times: list[float] = []

        @retry(max_attempts=3, delay=0.1)
        async def async_timed_fails() -> str:
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 3:
                raise ValueError("Not yet")
            return "done"

        await async_timed_fails()

        assert len(call_times) == 3
        assert call_times[1] - call_times[0] >= 0.09
        assert call_times[2] - call_times[1] >= 0.09


class TestRetryLogging:
    """Test that retry attempts are logged."""

    def test_logs_retry_attempt(self, caplog: pytest.LogCaptureFixture) -> None:
        call_count = 0

        @retry(max_attempts=3)
        def logged_fails() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Logged failure")
            return "done"

        with caplog.at_level(logging.WARNING):
            logged_fails()

        assert len([r for r in caplog.records if "Retrying" in r.message]) == 2

    def test_logs_exception_details(self, caplog: pytest.LogCaptureFixture) -> None:
        @retry(max_attempts=2)
        def specific_error() -> str:
            raise ValueError("Specific error message")

        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError):
                specific_error()

        assert any("Specific error message" in r.message for r in caplog.records)


class TestRetryDefaults:
    """Test default parameter values."""

    def test_default_max_attempts_is_three(self) -> None:
        call_count = 0

        @retry()
        def count_calls() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Keep counting")

        with pytest.raises(ValueError):
            count_calls()

        assert call_count == 3

    def test_default_delay_is_one_second(self) -> None:
        call_times: list[float] = []

        @retry(max_attempts=2)
        def timed() -> str:
            call_times.append(time.time())
            raise ValueError("Timing")

        with pytest.raises(ValueError):
            timed()

        assert len(call_times) == 2
        assert call_times[1] - call_times[0] >= 0.9


class TestFunctionMetadataPreservation:
    """Test that decorated functions preserve their metadata."""

    def test_preserves_function_name(self) -> None:
        @retry()
        def my_special_function() -> str:
            return "special"

        assert my_special_function.__name__ == "my_special_function"

    def test_preserves_docstring(self) -> None:
        @retry()
        def documented_function() -> str:
            """This is my docstring."""
            return "documented"

        assert documented_function.__doc__ == "This is my docstring."
