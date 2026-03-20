"""Langfuse Client Wrapper"""

import os
from langfuse import Langfuse


class LangfuseClientWrapper:
    """Wrapper around Langfuse client with convenience methods"""
    
    def __init__(self, public_key=None, secret_key=None, host=None):
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        if not self.public_key or not self.secret_key:
            raise ValueError(
                "Missing Langfuse credentials. Set LANGFUSE_PUBLIC_KEY and "
                "LANGFUSE_SECRET_KEY environment variables."
            )
        
        self.client = Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            host=self.host
        )
    
    def fetch_traces(self, **kwargs):
        """Fetch traces from Langfuse"""
        return self.client.fetch_traces(**kwargs)
    
    def fetch_trace(self, trace_id):
        """Fetch a specific trace"""
        return self.client.fetch_trace(trace_id)
    
    def fetch_observations(self, **kwargs):
        """Fetch observations"""
        return self.client.fetch_observations(**kwargs)
