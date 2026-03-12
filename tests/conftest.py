"""Test configuration and shared fixtures."""

import os

# Set test environment before importing anything
os.environ["COSMOS_HOST"] = "https://test.documents.azure.com:443/"
os.environ["COSMOS_KEY"] = "test-key"
os.environ["AI_FOUNDRY_ENDPOINT"] = "https://test.openai.azure.com/"
os.environ["AI_FOUNDRY_API_KEY"] = "test-key"
os.environ["DISABLE_AUTH"] = "true"
os.environ["ENVIRONMENT"] = "test"
