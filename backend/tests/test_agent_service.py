import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base
from app.models.config import AIConfig
from app.models.user import User


class AgentServiceInitTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.db.add(
            AIConfig(
                config_type="llm",
                provider_name="DeepSeek",
                base_url="https://api.deepseek.com",
                api_key="test-key",
                model_name="deepseek-chat",
                is_active=True
            )
        )
        self.user = User(username="tester", hashed_password="x", ai_preferences={})
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_init_without_embedding_config(self):
        from app.services.agent_service import AgentService

        fake_llm = MagicMock()
        fake_llm_with_tools = MagicMock()
        fake_llm.bind_tools.return_value = fake_llm_with_tools

        with patch("app.services.agent_service.ChatOpenAI", return_value=fake_llm):
            service = AgentService(self.db, self.user)

        self.assertIs(service.llm, fake_llm)
        self.assertIs(service.llm_with_tools, fake_llm_with_tools)


if __name__ == "__main__":
    unittest.main()
