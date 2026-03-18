"""Test configuration and shared fixtures."""

import os

# Set test environment before importing anything
os.environ["COSMOS_HOST"] = "https://test.documents.azure.com:443/"
os.environ["AI_FOUNDRY_ENDPOINT"] = "https://test.openai.azure.com/"
os.environ["DISABLE_AUTH"] = "true"
os.environ["OPENBRAIN_API_TOKEN"] = "test-token"
os.environ["ENVIRONMENT"] = "test"
