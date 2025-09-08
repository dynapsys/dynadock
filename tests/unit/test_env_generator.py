"""Unit tests for EnvGenerator."""

from __future__ import annotations

from unittest.mock import patch


from dynadock.env_generator import EnvGenerator


class TestEnvGenerator:
    """Test EnvGenerator functionality."""

    def test_init(self, temp_dir):
        env_path = temp_dir / ".env.test"
        gen = EnvGenerator(str(env_path))
        assert gen.env_file == env_path

    # ------------------------------------------------------------------
    # generate()
    # ------------------------------------------------------------------

    @patch("secrets.token_urlsafe")
    def test_generate_basic(self, mock_token, temp_dir):
        """Generate minimal env vars for two services with TLS enabled."""
        mock_token.side_effect = ["secret1", "secret2", "pass1", "pass2", "pass3"]
        env_file = temp_dir / ".env.test"
        generator = EnvGenerator(str(env_file))

        services = {
            "api": {"image": "node:18"},
            "frontend": {"image": "nginx"},
        }
        ports = {"api": 8001, "frontend": 8002}

        env_vars = generator.generate(
            services=services,
            ports=ports,
            domain="test.local",
            enable_tls=True,
            cors_origins=["https://app.com"],
        )

        # Check service variables
        assert env_vars["API_PORT"] == "8001"
        assert env_vars["API_URL"] == "https://api.test.local"
        assert env_vars["FRONTEND_PORT"] == "8002"
        # Secrets
        assert env_vars["DYNADOCK_SECRET_KEY"] == "secret1"
        assert env_file.exists()

    @patch("secrets.token_urlsafe")
    def test_generate_with_database(self, mock_token, temp_dir):
        """Generate env vars for common databases."""
        mock_token.return_value = "testpass"
        env_file = temp_dir / ".env.test"
        generator = EnvGenerator(str(env_file))

        services = {
            "postgres": {"image": "postgres:15"},
            "mysql": {"image": "mysql:8"},
            "mongodb": {"image": "mongo:6"},
            "redis": {"image": "redis:7"},
        }
        ports = {
            "postgres": 5432,
            "mysql": 3306,
            "mongodb": 27017,
            "redis": 6379,
        }

        env_vars = generator.generate(
            services=services,
            ports=ports,
            domain="db.local",
            enable_tls=False,
            cors_origins=[],
        )

        assert "POSTGRES_PASSWORD" in env_vars
        assert "MYSQL_DATABASE" in env_vars
        assert "MONGODB_URI" in env_vars
        assert "REDIS_URL" in env_vars
