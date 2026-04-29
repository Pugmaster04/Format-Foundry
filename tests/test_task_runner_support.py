import unittest

from modular_file_utility_suite import OperationCanceledError
import task_runner_support


class TaskRunnerSupportTests(unittest.TestCase):
    def test_execute_action_reports_success_and_done_message(self) -> None:
        events: list[str] = []

        def action() -> None:
            events.append("action")

        task_runner_support.execute_action(
            action,
            task_name="Task X",
            cancel_exception_type=OperationCanceledError,
            done_message="done",
            on_success=lambda: events.append("success"),
            info_cb=lambda message: events.append(f"info:{message}"),
        )

        self.assertEqual(events, ["action", "success", "info:done"])

    def test_execute_action_routes_cancellation(self) -> None:
        events: list[str] = []

        def action() -> None:
            raise OperationCanceledError("stop now")

        task_runner_support.execute_action(
            action,
            task_name="Task X",
            cancel_exception_type=OperationCanceledError,
            on_cancel=lambda exc: events.append(f"cancel:{exc}"),
            log_cb=lambda message: events.append(f"log:{message}"),
        )

        self.assertEqual(events, ["log:stop now", "cancel:stop now"])

    def test_execute_action_routes_errors_and_finally(self) -> None:
        events: list[str] = []

        def action() -> None:
            raise RuntimeError("boom")

        task_runner_support.execute_action(
            action,
            cancel_exception_type=OperationCanceledError,
            on_error=lambda exc: events.append(f"error:{exc}"),
            on_finally=lambda: events.append("finally"),
            log_cb=lambda message: events.append(f"log:{message}"),
            error_cb=lambda message: events.append(f"ui:{message}"),
            task_name="Task X",
        )

        self.assertEqual(
            events,
            [
                "log:Error: boom",
                "error:boom",
                "ui:Task X failed:\nboom",
                "finally",
            ],
        )


if __name__ == "__main__":
    unittest.main()
