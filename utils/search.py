import requests
import os
import json
from flask import current_app

def search_serpapi(query, api_key=None, num_results=5):
    """
    Search using SerpAPI and return results
    
    Args:
        query (str): Search query
        api_key (str): SerpAPI API key (optional, will use from config if not provided)
        num_results (int): Number of results to return
    
    Returns:
        list: List of search result dictionaries
    """
    try:
        # Get API key from parameter, app config, or environment
        if not api_key:
            api_key = current_app.config.get('SERPAPI_API_KEY') or os.environ.get('SERPAPI_API_KEY')
        
        if not api_key:
            raise ValueError("SerpAPI key not found in environment or app config")
        
        # Set up request parameters
        base_url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": num_results
        }
        
        # Make the request
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Extract and format results
        results = []
        if "organic_results" in data:
            for result in data["organic_results"]:
                entry = {
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0)
                }
                results.append(entry)
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error with SerpAPI request: {str(e)}")
        return []
    except ValueError as e:
        print(f"Error with SerpAPI configuration: {str(e)}")
        return []
    except Exception as e:
        print(f"Unexpected error with SerpAPI: {str(e)}")
        return []

def deduplicate_results(results):
    """
    Deduplicate search results by URL
    
    Args:
        results (list): List of search result dictionaries
    
    Returns:
        list: Deduplicated list of search results
    """
    seen_urls = set()
    unique_results = []
    
    for result in results:
        url = result.get("link", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)
    
    return unique_results

# Optional: Add mock search function for development/testing
def mock_search(query, num_results=5):
    """Mock search function for development and testing"""
    mock_results = [
        {
            "title": f"Mock Result 1 for {query}",
            "link": "https://example.com/result1",
            "snippet": f"This is a mock search result for {query} with some sample text for testing purposes.",
            "position": 1
        },
        {
            "title": f"Mock Result 2 for {query}",
            "link": "https://example.com/result2",
            "snippet": f"Another mock result for testing the {query} search functionality without using real API calls.",
            "position": 2
        }
    ]
    
    # Generate additional mock results if needed
    for i in range(3, num_results + 1):
        mock_results.append({
            "title": f"Mock Result {i} for {query}",
            "link": f"https://example.com/result{i}",
            "snippet": f"Sample search result #{i} for query: {query}",
            "position": i
        })
    
    return mock_results[:num_results]
