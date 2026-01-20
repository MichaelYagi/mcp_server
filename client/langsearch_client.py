"""
LangSearch API Client
Provides web search capabilities as a fallback when no appropriate tools are found.
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any


class LangSearchClient:
    """Client for LangSearch web search API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LangSearch client.

        Args:
            api_key: LangSearch API key. If None, reads from LANGSEARCH_TOKEN env variable.
        """
        self.api_key = api_key or os.getenv("LANGSEARCH_TOKEN", "").strip()
        self.endpoint = "https://api.langsearch.com/v1/web-search"
        self.logger = logging.getLogger("mcp_client")

    def is_available(self) -> bool:
        """Check if LangSearch is configured and available"""
        return bool(self.api_key)

    async def search(self, query: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Perform a web search using LangSearch API.

        Args:
            query: The search query string
            timeout: Request timeout in seconds

        Returns:
            Dict with keys:
                - success (bool): Whether the search succeeded
                - results (str): Search results text if successful
                - error (str): Error message if failed
        """
        if not self.is_available():
            self.logger.warning("🔍 LangSearch API key not configured")
            return {
                "success": False,
                "error": "LangSearch API key not configured. Set LANGSEARCH_TOKEN environment variable."
            }

        try:
            self.logger.info(f"🔍 Performing LangSearch web search: '{query[:100]}'")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "query": query
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload
                )

                # Check for HTTP errors
                if response.status_code == 401:
                    self.logger.error("❌ LangSearch: Invalid API key")
                    return {
                        "success": False,
                        "error": "Invalid LangSearch API key"
                    }
                elif response.status_code == 429:
                    self.logger.error("❌ LangSearch: Rate limit exceeded")
                    return {
                        "success": False,
                        "error": "LangSearch rate limit exceeded. Please try again later."
                    }
                elif response.status_code >= 400:
                    self.logger.error(f"❌ LangSearch: HTTP {response.status_code}")
                    return {
                        "success": False,
                        "error": f"LangSearch API error: HTTP {response.status_code}"
                    }

                response.raise_for_status()
                data = response.json()

                # Extract search results
                # Adjust this based on actual LangSearch API response format
                results = data.get("results", data.get("data", str(data)))

                self.logger.info(f"✅ LangSearch returned results ({len(str(results))} chars)")

                return {
                    "success": True,
                    "results": results,
                    "raw_response": data
                }

        except httpx.TimeoutException:
            self.logger.error("❌ LangSearch: Request timeout")
            return {
                "success": False,
                "error": "LangSearch request timed out"
            }
        except httpx.HTTPError as e:
            self.logger.error(f"❌ LangSearch HTTP error: {e}")
            return {
                "success": False,
                "error": f"LangSearch HTTP error: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"❌ LangSearch unexpected error: {e}")
            return {
                "success": False,
                "error": f"LangSearch error: {str(e)}"
            }


# Global instance
_langsearch_client = None


def get_langsearch_client() -> LangSearchClient:
    """Get or create global LangSearch client instance"""
    global _langsearch_client
    if _langsearch_client is None:
        _langsearch_client = LangSearchClient()
    return _langsearch_client