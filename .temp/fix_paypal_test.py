path = r"G:\projects\ai数据隐私隔离\tests\test_payment.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the TestPayPalClient class start and end
start_line = None
end_line = None
for i, line in enumerate(lines):
    if line.strip() == "class TestPayPalClient:":
        start_line = i
    if start_line is not None and line.strip() == "class TestDatabaseLicense:":
        end_line = i
        break

if start_line is None or end_line is None:
    print(f"Could not find boundaries: start={start_line}, end={end_line}")
    exit(1)

# New PayPal test class
new_paypal_class = '''class TestPayPalClient:
    @pytest.fixture
    def paypal_client(self):
        from payment import PayPalClient
        return PayPalClient(client_id="test_id", client_secret="test_secret", mode="sandbox")

    def _make_fake_response(self, status_code, json_data, text=""):
        """Create a simple fake httpx response."""
        class FakeResponse:
            def __init__(self, sc, jd, txt):
                self.status_code = sc
                self._json = jd
                self.text = txt
            def json(self):
                return self._json
        return FakeResponse(status_code, json_data, text)

    def _fake_async_client_factory(self, post_side_effect):
        """Create a factory for FakeClient that wraps httpx.AsyncClient context manager."""
        import asyncio

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self._responses = post_side_effect if isinstance(post_side_effect, list) else [post_side_effect]
                self._idx = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, *args, **kwargs):
                if self._idx >= len(self._responses):
                    raise RuntimeError("No more mock responses")
                resp = self._responses[self._idx]
                self._idx += 1
                return resp

        return FakeClient

    @pytest.mark.asyncio
    async def test_create_order_success(self, paypal_client):
        auth_r = self._make_fake_response(200, {"access_token": "tok"})
        order_r = self._make_fake_response(201, {"id": "ORD123", "status": "CREATED"})
        FakeClientCls = self._fake_async_client_factory([auth_r, order_r])

        with patch("payment.httpx.AsyncClient", new=FakeClientCls):
            paypal_client._access_token = None
            result = await paypal_client.create_order(amount=99.0, tier="pro", email="t@t.com")
            assert result["id"] == "ORD123"

    @pytest.mark.asyncio
    async def test_create_order_auth_failure(self, paypal_client):
        from payment import PayPalError
        auth_r = self._make_fake_response(401, {}, text="Unauthorized")
        FakeClientCls = self._fake_async_client_factory(auth_r)

        with patch("payment.httpx.AsyncClient", new=FakeClientCls):
            paypal_client._access_token = None
            with pytest.raises(PayPalError):
                await paypal_client.create_order(amount=99.0, tier="pro")

    @pytest.mark.asyncio
    async def test_capture_order_success(self, paypal_client):
        auth_r = self._make_fake_response(200, {"access_token": "tok"})
        cap_r = self._make_fake_response(201, {"id": "CAP123", "status": "COMPLETED"})
        FakeClientCls = self._fake_async_client_factory([auth_r, cap_r])

        with patch("payment.httpx.AsyncClient", new=FakeClientCls):
            paypal_client._access_token = None
            result = await paypal_client.capture_order("ORD123")
            assert result["status"] == "COMPLETED"

    def test_get_paypal_client_no_config(self):
        with patch.dict(os.environ, {}, clear=True):
            from payment import get_paypal_client
            assert get_paypal_client() is None

    def test_verify_webhook_sandbox(self, paypal_client):
        paypal_client.webhook_id = "WH_TEST"
        headers = {
            "paypal-transmission-id": "txn_1",
            "paypal-transmission-time": "2024-01-01T00:00:00Z",
            "paypal-transmission-sig": "sig",
            "paypal-cert-url": "https://certs.paypal.com",
        }
        assert paypal_client.verify_webhook_signature(headers, json.dumps({"x": 1}))

    def test_verify_webhook_missing_headers(self, paypal_client):
        paypal_client.webhook_id = "WH_TEST"
        assert not paypal_client.verify_webhook_signature({}, "{}")

'''

# Replace the class
new_lines = lines[:start_line] + [new_paypal_class] + lines[end_line:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print(f"Replaced TestPayPalClient (lines {start_line+1}-{end_line+1})")
