import json
import unittest
from unittest import mock

import aria2_support


class Aria2SupportTests(unittest.TestCase):
    def test_build_rpc_payload_uses_expected_shape(self) -> None:
        payload = aria2_support.build_rpc_payload("pauseAll", [1, 2], request_id="req-1")

        self.assertEqual(
            payload,
            {
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "aria2.pauseAll",
                "params": [1, 2],
            },
        )

    def test_build_rpc_request_targets_local_rpc_endpoint(self) -> None:
        request = aria2_support.build_rpc_request(6800, "tellActive", [["gid"]], request_id="req-2")

        self.assertEqual(request.full_url, "http://127.0.0.1:6800/jsonrpc")
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "jsonrpc": "2.0",
                "id": "req-2",
                "method": "aria2.tellActive",
                "params": [["gid"]],
            },
        )

    def test_call_rpc_returns_result_field(self) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b'{\"result\": [\"gid-1\"]}'

        opener = mock.Mock(return_value=FakeResponse())

        result = aria2_support.call_rpc(6801, "tellActive", [["gid"]], opener=opener)

        self.assertEqual(result, ["gid-1"])
        opener.assert_called_once()

    def test_process_is_running_handles_none_and_finished_processes(self) -> None:
        running = mock.Mock()
        running.poll.return_value = None
        finished = mock.Mock()
        finished.poll.return_value = 0

        self.assertFalse(aria2_support.process_is_running(None))
        self.assertTrue(aria2_support.process_is_running(running))
        self.assertFalse(aria2_support.process_is_running(finished))


if __name__ == "__main__":
    unittest.main()
