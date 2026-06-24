import sys
import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import orchestrator
from src.schemas import JobPosting

class TestQwenOrchestrator(unittest.IsolatedAsyncioTestCase):
    
    @patch("src.orchestrator.client")
    async def test_run_agent_step_parse_success(self, mock_client):
        # Setup mock for client.beta.chat.completions.parse
        mock_parsed = JobPosting(
            embassy_name="KBRI Singapore",
            job_title="Staf Setempat",
            is_embassy_local_staff=True,
            requirements=["Degree in IT", "Fluent in English"],
            application_deadline="2026-12-31",
            contact_email="recruitment@kbri.sg"
        )
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed
        mock_response.choices = [mock_choice]
        
        # Assign mock to client.beta.chat.completions.parse
        mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
        
        # Run step
        result = await orchestrator.run_agent_step(
            config=orchestrator.monitor_config,
            prompt="Analyze scraped text",
            step_name="Monitor Agent"
        )
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["embassy_name"], "KBRI Singapore")
        self.assertEqual(result["job_title"], "Staf Setempat")
        self.assertTrue(result["is_embassy_local_staff"])
        self.assertEqual(result["contact_email"], "recruitment@kbri.sg")
        
        # Ensure it was called with beta.chat.completions.parse
        mock_client.beta.chat.completions.parse.assert_called_once()
        
    @patch("src.orchestrator.client")
    async def test_run_agent_step_fallback(self, mock_client):
        # Make the beta parse call raise an exception to trigger the JSON mode fallback
        mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("parse method not supported by Ollama endpoint"))
        
        # Setup mock for client.chat.completions.create
        mock_json_content = """{
            "fit_score": 90,
            "matching_strengths": ["Python expertise", "AWS knowledge", "Communication"],
            "missing_skills": ["Diplomatic protocol"],
            "is_suitable": true
        }"""
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = mock_json_content
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Run step
        result = await orchestrator.run_agent_step(
            config=orchestrator.matcher_config,
            prompt="Compare resume",
            step_name="Matcher Agent"
        )
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["fit_score"], 90)
        self.assertEqual(result["matching_strengths"], ["Python expertise", "AWS knowledge", "Communication"])
        self.assertTrue(result["is_suitable"])
        
        # Verify fallback triggers create
        mock_client.chat.completions.create.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_scrape_instagram_post_with_session(self, mock_urlopen):
        import json
        import os
        # Mock HTTP response containing Instagram items JSON
        mock_json = {
            "items": [
                {
                    "caption": {
                        "text": "Lowongan Kerja Staf Setempat di KBRI Singapura. Persyaratan..."
                    }
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_json).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        from src.tools.scraper import scrape_kbri_portal
        
        with patch.dict(os.environ, {"INSTAGRAM_SESSION_ID": "mock-session-123"}):
            result = scrape_kbri_portal("https://www.instagram.com/p/C8o7U4hSa4Q/")
            
        self.assertIn("Lowongan Kerja Staf Setempat", result)
        self.assertIn("Instagram Post (C8o7U4hSa4Q) Caption", result)

    @patch("urllib.request.urlopen")
    def test_scrape_instagram_profile_with_session(self, mock_urlopen):
        import json
        import os
        # Mock HTTP response containing Instagram profile JSON
        mock_json = {
            "data": {
                "user": {
                    "full_name": "KBRI Singapura",
                    "edge_owner_to_timeline_media": {
                        "edges": [
                            {
                                "node": {
                                    "shortcode": "C8o7U4hSa4Q",
                                    "edge_media_to_caption": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "text": "Open Recruitment KBRI Singapura"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_json).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        from src.tools.scraper import scrape_kbri_portal
        
        with patch.dict(os.environ, {"INSTAGRAM_SESSION_ID": "mock-session-123"}):
            result = scrape_kbri_portal("https://www.instagram.com/kbri.singapura/")
            
        self.assertIn("Open Recruitment KBRI Singapura", result)
        self.assertIn("Instagram Profile: @kbri.singapura", result)

if __name__ == "__main__":
    unittest.main()
