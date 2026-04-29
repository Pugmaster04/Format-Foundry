from typing import Any, Callable


def execute_action(
    action: Callable[[], Any],
    *,
    task_name: str,
    cancel_exception_type: type[BaseException],
    on_success: Callable[[], None] | None = None,
    on_cancel: Callable[[BaseException], None] | None = None,
    on_error: Callable[[Exception], None] | None = None,
    on_finally: Callable[[], None] | None = None,
    done_message: str | None = None,
    info_cb: Callable[[str], None] | None = None,
    error_cb: Callable[[str], None] | None = None,
    log_cb: Callable[[str], None] | None = None,
) -> None:
    try:
        action()
        if on_success is not None:
            on_success()
        if done_message and info_cb is not None:
            info_cb(done_message)
    except cancel_exception_type as exc:
        if log_cb is not None:
            log_cb(str(exc))
        if on_cancel is not None:
            on_cancel(exc)
    except Exception as exc:
        if log_cb is not None:
            log_cb(f"Error: {exc}")
        if on_error is not None:
            on_error(exc)
        if error_cb is not None:
            error_cb(f"{task_name} failed:\n{exc}")
    finally:
        if on_finally is not None:
            on_finally()
