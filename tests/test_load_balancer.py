"""load_balancer.py — 负载均衡测试"""
import pytest
from load_balancer import UpstreamNode, LoadBalancer


class TestUpstreamNode:
    def test_default_values(self):
        node = UpstreamNode(url="https://api.openai.com")
        assert node.url == "https://api.openai.com"
        assert node.healthy is True
        assert node.last_health_check == 0.0
        assert node.active_connections == 0
        assert node.consecutive_failures == 0


class TestLoadBalancerBasic:
    def test_empty_urls(self):
        lb = LoadBalancer([])
        assert lb.get_upstream() is None

    def test_single_node_round_robin(self):
        lb = LoadBalancer(["https://api.openai.com"])
        url = lb.get_upstream()
        assert url == "https://api.openai.com"

    def test_round_robin_distributes(self):
        urls = ["https://a.com", "https://b.com"]
        lb = LoadBalancer(urls, strategy="round_robin")
        seen = set()
        for _ in range(10):
            seen.add(lb.get_upstream())
        assert seen == {"https://a.com", "https://b.com"}

    def test_random_strategy(self):
        urls = ["https://a.com", "https://b.com"]
        lb = LoadBalancer(urls, strategy="random")
        # Should not raise, returns one of the URLs
        url = lb.get_upstream()
        assert url in urls

    def test_least_connections_strategy(self):
        urls = ["https://a.com", "https://b.com"]
        lb = LoadBalancer(urls, strategy="least_connections")
        url = lb.get_upstream()
        assert url in urls
        assert lb._find_node(url).active_connections == 1


class TestLoadBalancerFailure:
    def test_mark_failure_increments_counter(self):
        urls = ["https://a.com"]
        lb = LoadBalancer(urls)
        lb.mark_failure("https://a.com")
        node = lb._find_node("https://a.com")
        assert node.consecutive_failures == 1

    def test_mark_failure_threshold_marks_unhealthy(self):
        urls = ["https://a.com"]
        lb = LoadBalancer(urls)
        for _ in range(LoadBalancer.MAX_CONSECUTIVE_FAILURES):
            lb.mark_failure("https://a.com")
        node = lb._find_node("https://a.com")
        assert node.healthy is False

    def test_mark_success_resets_failure_count(self):
        urls = ["https://a.com"]
        lb = LoadBalancer(urls)
        lb.mark_failure("https://a.com")
        lb.mark_failure("https://a.com")
        lb.mark_success("https://a.com")
        node = lb._find_node("https://a.com")
        assert node.consecutive_failures == 0

    def test_unhealthy_node_not_returned(self):
        urls = ["https://a.com", "https://b.com"]
        lb = LoadBalancer(urls)
        # Mark b.com as unhealthy
        for _ in range(LoadBalancer.MAX_CONSECUTIVE_FAILURES):
            lb.mark_failure("https://b.com")
        # Should only return a.com
        urls_seen = {lb.get_upstream() for _ in range(10)}
        assert urls_seen == {"https://a.com"}

    def test_all_unhealthy_returns_none(self):
        urls = ["https://a.com", "https://b.com"]
        lb = LoadBalancer(urls)
        for url in urls:
            for _ in range(LoadBalancer.MAX_CONSECUTIVE_FAILURES):
                lb.mark_failure(url)
        assert lb.get_upstream() is None

    def test_mark_failure_unknown_url_noop(self):
        lb = LoadBalancer(["https://a.com"])
        lb.mark_failure("https://unknown.com")  # should not raise

    def test_mark_success_unknown_url_noop(self):
        lb = LoadBalancer(["https://a.com"])
        lb.mark_success("https://unknown.com")  # should not raise


class TestLoadBalancerStats:
    def test_get_stats_returns_all_nodes(self):
        urls = ["https://a.com", "https://b.com"]
        lb = LoadBalancer(urls)
        stats = lb.get_stats()
        assert len(stats) == 2
        assert stats[0]["url"] == "https://a.com"

    def test_stats_reflects_node_state(self):
        lb = LoadBalancer(["https://a.com"])
        for _ in range(LoadBalancer.MAX_CONSECUTIVE_FAILURES):
            lb.mark_failure("https://a.com")
        stats = lb.get_stats()
        assert stats[0]["healthy"] is False
        assert stats[0]["consecutive_failures"] == LoadBalancer.MAX_CONSECUTIVE_FAILURES


class TestLoadBalancerRelease:
    def test_release_decrements_counter(self):
        urls = ["https://a.com"]
        lb = LoadBalancer(urls)
        lb.get_upstream()  # active_connections = 1
        lb.release("https://a.com")
        node = lb._find_node("https://a.com")
        assert node.active_connections == 0

    def test_release_does_not_go_below_zero(self):
        urls = ["https://a.com"]
        lb = LoadBalancer(urls)
        lb.release("https://a.com")  # no connections, should stay at 0
        node = lb._find_node("https://a.com")
        assert node.active_connections == 0
