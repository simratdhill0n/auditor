"""AI Agent - Intelligent API interaction and data fetching."""

import json
import logging
from typing import Any, Optional

import requests

from services.deepseek_service import ask_llm

# Setup logging with more detail
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s] %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class AuditResult:
    """Result wrapper for agent operations."""

    def __init__(self, success: bool, result: Any = None, error: str = None):
        self.success = success
        self.result = result
        self.error = error


class APIAgent:
    """AI Agent that learns from API documentation and makes intelligent calls."""

    CKAN_API_DOCS = """
    # CKAN API Documentation (open.canada.ca)
    
    ## Base URL
    https://open.canada.ca/data/api
    
    ## Package Search Endpoint
    GET /3/action/package_search
    
    Parameters:
    - q: Search query string (dataset name, keywords)
    - rows: Number of results (default: 10, max: 1000)
    - start: Offset for pagination (default: 0)
    - sort: Sort order (e.g., "metadata_modified desc")
    - fq: Filter query (e.g., "type:dataset")
    - include_private: Include private datasets (default: false)
    
    Response:
    {
        "success": true,
        "result": {
            "count": total_count,
            "records": [
                {
                    "id": dataset_id,
                    "name": dataset_name,
                    "title": dataset_title,
                    "notes": description,
                    "resources": [
                        {
                            "id": resource_id,
                            "name": resource_name,
                            "format": "CSV" | "JSON" | "XLS" etc,
                            "url": download_url,
                            "description": resource_description
                        }
                    ]
                }
            ]
        }
    }
    """

    def __init__(self):
        self.base_url = "https://open.canada.ca/data/api"
        self.session = requests.Session()
        self.session.timeout = 30

    def _search_datasets(self, query: str, limit: int = 5) -> AuditResult:
        """Search CKAN API for datasets."""
        try:
            url = f"{self.base_url}/3/action/package_search"
            params = {
                "q": query,
                "rows": min(limit, 10),
                "sort": "metadata_modified desc",
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                return AuditResult(
                    False, error=f"CKAN API error: {data.get('error', 'Unknown')}"
                )

            # FIX #1: CKAN returns "results" not "records"
            records = data.get("result", {}).get("results", [])
            return AuditResult(success=True, result=records)

        except requests.Timeout:
            return AuditResult(False, error="CKAN API timeout")
        except requests.RequestException as e:
            return AuditResult(False, error=f"API connection error: {str(e)}")
        except Exception as e:
            return AuditResult(False, error=f"Search error: {str(e)}")

    def _get_direct_download_url(self, resource_url: str, resource_format: str) -> Optional[str]:
        """
        Transform resource URL to direct download format.
        Some CKAN URLs point to landing pages, need to find actual CSV.
        """
        logger.debug(f"      🔗 Original URL: {resource_url[:80]}")
        
        # If already a direct CSV URL, use it
        if resource_url.endswith('.csv'):
            return resource_url
        
        # If it's a CKAN DataStore URL, convert to CSV export
        if '/datastore_search' in resource_url or 'datastore_id=' in resource_url:
            # Extract datastore ID
            if 'datastore_id=' in resource_url:
                import re
                match = re.search(r'datastore_id=([^&]+)', resource_url)
                if match:
                    ds_id = match.group(1)
                    # Try CSV export endpoint
                    csv_url = f"https://open.canada.ca/data/api/3/action/datastore_search_sql?sql=SELECT%20*%20FROM%20%22{ds_id}%22&format=csv"
                    logger.debug(f"      🔄 Converted to CSV export URL")
                    return csv_url
        
        # If it's an HTML page, try to append /download
        if 'http' in resource_url:
            if not resource_url.endswith(('.csv', '.json', '.xlsx')):
                # Try common download patterns
                candidates = [
                    resource_url + '/download',
                    resource_url.replace('/dataset/', '/dataset-file/'),
                    resource_url.split('?')[0] + '?format=csv',
                ]
                logger.debug(f"      🔄 Trying alternative URLs...")
                return candidates[0]  # Return first candidate to try
        
        return resource_url
        """
        Fetch CSV data by trying multiple methods:
        1. Direct CSV download
        2. CKAN DataStore API (if datastore_id available)
        3. Skip if metadata only
        """
        try:
            import csv
            import io
            
            # Transform URL to get direct download if needed
            download_url = self._get_direct_download_url(url, "CSV")
            logger.debug(f"      📥 Fetching from URL: {download_url[:80]}...")
            csv_text = None
            
            # Try Method 1: Direct CSV download
            try:
                response = self.session.get(download_url, timeout=10)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                logger.debug(f"      Content-Type: {content_type}")
                
                # Skip HTML pages (landing pages, not data)
                if 'text/html' in content_type:
                    logger.debug(f"      ⚠️  Got HTML page, not CSV data")
                    # Try to extract DataStore ID from HTML
                    if '"datastore_' in response.text:
                        logger.debug(f"      📍 Found DataStore reference, will try API...")
                    else:
                        return None
                else:
                    csv_text = response.text
                    logger.debug(f"      ✅ Got CSV file (Content-Type: {content_type})")
                    
            except Exception as e:
                logger.debug(f"      Direct download failed: {e}")
            
            # If direct download didn't work, try CKAN DataStore API
            # Extract dataset ID from URL and try DataStore
            if not csv_text:
                logger.debug(f"      Trying CKAN DataStore API...")
                # This is a fallback - in production would need to extract proper IDs
                return None
            
            # Parse CSV
            csv_file = io.StringIO(csv_text)
            reader = csv.DictReader(csv_file)
            rows = list(reader)[:max_rows]
            
            if not rows:
                logger.debug(f"      ❌ CSV is empty, skip")
                return None
            
            logger.debug(f"      ✅ Loaded {len(rows)} rows")
            logger.debug(f"      📊 First row: {rows[0]}")
            
            # QUALITY CHECK: Is this ACTUAL DATA or METADATA?
            # Check 1: Values shouldn't be very long text (> 100 chars average)
            first_row = rows[0]
            value_lengths = [len(str(v)) for v in first_row.values()]
            avg_value_length = sum(value_lengths) / len(value_lengths) if value_lengths else 0
            max_value_length = max(value_lengths) if value_lengths else 0
            
            if avg_value_length > 100 or max_value_length > 500:
                logger.debug(f"      ⚠️  Looks like METADATA (long text), not data")
                logger.debug(f"         Avg: {avg_value_length:.0f}ch, Max: {max_value_length}ch")
                return None
            
            # Check 2: Data should have NUMERIC values
            has_numbers = False
            for row in rows[:min(10, len(rows))]:
                for value in row.values():
                    try:
                        float(str(value).replace(',', '').replace('%', ''))
                        has_numbers = True
                        break
                    except:
                        pass
                if has_numbers:
                    break
            
            if not has_numbers:
                logger.debug(f"      ⚠️  No numeric values - this is METADATA, not data")
                return None
            
            # FINAL CHECK: Reject if this looks like dataset descriptions, not actual data
            analysis_text = str(rows).lower()
            
            # If response talks ABOUT datasets instead of showing data, reject it
            metadata_phrases = [
                "this table contains",
                "not all combinations",
                "no longer being released",
                "dimensions",
                "series",
                "data described by"
            ]
            
            if any(phrase in analysis_text for phrase in metadata_phrases):
                logger.debug(f"      ❌ This is METADATA (descriptions), not actual data!")
                logger.debug(f"         Content: {analysis_text[:100]}")
                return None
            all_columns = list(rows[0].keys()) if rows else []
            query_keywords = query.lower().split()
            all_text = str(rows).lower()
            matching_keywords = sum(1 for kw in query_keywords if kw in all_text)
            relevance_score = (matching_keywords / len(query_keywords)) * 100 if query_keywords else 0
            
            # Do column names match what query needs?
            column_text = " ".join(all_columns).lower()
            
            # Province queries need province/geo/region column
            if any(kw in query.lower() for kw in ['province', 'provincial', 'by province']):
                has_province_col = any(kw in column_text for kw in ['province', 'geo', 'region', 'location', 'area'])
                if not has_province_col:
                    logger.debug(f"      ⚠️  Query needs 'province' column but columns are: {all_columns}")
                    return None
            
            logger.debug(f"      Relevance: {relevance_score:.0f}%")
            logger.debug(f"      Columns: {all_columns}")
            
            if relevance_score < 50:
                logger.debug(f"      ⚠️  Not relevant ({relevance_score:.0f}%), skip")
                return None
            
            # CHECK 2: Only check RECENCY if query asks for it
            recency_keywords = ['latest', 'recent', 'current', 'new', 'updated']
            asks_for_recent = any(kw in query.lower() for kw in recency_keywords)
            
            if asks_for_recent:
                # User asked for recent data - check for 2023/2024
                date_keywords = ['2024', '2023', 'latest', 'current', 'recent']
                has_recent_data = any(kw in all_text for kw in date_keywords)
                
                logger.debug(f"      Query asks for RECENT: {asks_for_recent}")
                logger.debug(f"      Has recent data (2023/2024): {has_recent_data}")
                
                if not has_recent_data:
                    logger.debug(f"      ❌ Too old (no 2023/2024 data), skip")
                    return None
            else:
                # User didn't ask for recent - use any data
                logger.debug(f"      Query doesn't ask for recent - accepting any data")
            
            # Dataset IS relevant (and recent if needed)! Keep ALL columns
            all_columns = list(rows[0].keys()) if rows else []
            logger.debug(f"      ✅ GOOD! Columns: {all_columns}")
            
            return {
                "data": rows,  # All rows
                "columns": all_columns,  # ALL columns
                "relevance_score": relevance_score,
                "row_count": len(rows)
            }
        except Exception as e:
            logger.debug(f"      Error: {e}")
            return None

    def _fetch_from_statcan_datastore(self, table_id: str, query: str) -> Optional[dict]:
        """
        Fetch ACTUAL DATA from Statistics Canada DataStore API.
        NOT metadata descriptions - real data rows with numbers!
        """
        try:
            logger.debug(f"      📡 Fetching from Stats Canada DataStore: {table_id}")
            
            # Stats Canada DataStore API
            url = "https://www150.statcan.gc.ca/api/tables.php"
            params = {
                "id": table_id,
                "limit": 100,
                "lang": "E"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("data"):
                logger.debug(f"      ❌ No data returned from DataStore")
                return None
            
            rows = data.get("data", [])[:100]
            
            if not rows:
                logger.debug(f"      ❌ Empty data")
                return None
            
            logger.debug(f"      ✅ Got {len(rows)} rows from DataStore")
            
            # Check if has actual numbers
            has_numbers = False
            for row in rows[:10]:
                for value in row:
                    try:
                        if isinstance(value, (int, float)):
                            has_numbers = True
                            break
                    except:
                        pass
                if has_numbers:
                    break
            
            if not has_numbers:
                logger.debug(f"      ⚠️  No numeric data found")
                return None
            
            logger.debug(f"      ✅ Has numeric data!")
            
            return {
                "data": rows,
                "columns": data.get("columns", []),
                "relevance_score": 85,
                "row_count": len(rows)
            }
            
        except Exception as e:
            logger.debug(f"      Error fetching from DataStore: {e}")
            return None
    
    def analyze_with_data(self, user_query: str, limit: int = 5) -> AuditResult:
        """
        Pipeline: search → fetch CSV → check DATASET relevance → skip irrelevant → analyze REAL DATA
        Keeps ALL columns for future multi-query use.
        """
        try:
            # STEP 1: Search for datasets
            logger.info(f"\n{'='*80}")
            logger.info(f"🔍 STEP 1: Searching for datasets matching '{user_query}'")
            
            search_results = self._search_datasets(user_query, limit)
            if not search_results.success:
                logger.error(f"❌ Search failed: {search_results.error}")
                return search_results

            datasets = search_results.result or []
            logger.info(f"✅ Found {len(datasets)} datasets")
            
            if not datasets:
                return AuditResult(False, error="No datasets found")

            # STEP 2: Try each dataset, skip irrelevant ones
            logger.info(f"\n📊 STEP 2: Fetching & checking DATASET relevance")
            best_dataset = None
            best_data = None
            datasets_tried = 0
            
            for i, ds in enumerate(datasets[:10]):  # Try up to 10 datasets
                logger.info(f"\n  Dataset {i+1}: {ds.get('title', 'Unknown')}")
                datasets_tried += 1
                
                try:
                    dataset_id = ds.get("id")
                    if not dataset_id:
                        logger.warning(f"    ⚠️  No ID, skip")
                        continue
                    
                    logger.debug(f"    Fetching resources...")
                    dataset_url = f"{self.base_url}/3/action/package_show"
                    detail_response = self.session.get(
                        dataset_url, params={"id": dataset_id}, timeout=10
                    )
                    detail_response.raise_for_status()
                    detail_data = detail_response.json()
                    
                    if not detail_data.get("success"):
                        logger.warning(f"    ⚠️  CKAN error, skip")
                        continue
                    
                    package = detail_data.get("result", {})
                    resources = package.get("resources", [])
                    logger.debug(f"    Found {len(resources)} resources")
                    
                    # Try each CSV resource
                    for resource in resources:
                        res_format = resource.get("format", "").upper()
                        res_url = resource.get("url", "")
                        res_name = resource.get("name", "Unknown")
                        
                        if res_format not in ["CSV", "JSON"]:
                            continue
                        
                        logger.info(f"    Resource: {res_name} ({res_format})")
                        
                        # CHECK if DATASET is relevant
                        dataset_data = self._fetch_and_check_dataset(res_url, user_query)
                        
                        if dataset_data:
                            # Dataset IS relevant (and recent if asked)!
                            logger.info(f"    ✅ RELEVANT! ({dataset_data['relevance_score']:.0f}%)")
                            logger.info(f"       Rows: {dataset_data['row_count']}")
                            logger.info(f"       Columns: {len(dataset_data['columns'])} (keeping all)")
                            
                            best_dataset = {
                                "title": ds.get("title", "Unknown"),
                                "name": ds.get("name", ""),
                                "resource_name": res_name,
                                "resource_format": res_format,
                                "resource_url": res_url
                            }
                            best_data = dataset_data
                            break
                    
                    if best_data:
                        break  # Found relevant dataset, stop searching
                        
                except Exception as e:
                    logger.debug(f"    Error: {e}")
                    continue

            if not best_data:
                logger.error(f"❌ No relevant datasets found (tried {datasets_tried})")
                return AuditResult(False, error="No relevant data found")

            # FINAL QUALITY CHECK: Check if actual data rows contain metadata text
            # Some datasets return CSV with descriptions as "data" rows
            sample_content = str(best_data['data'][:5]).lower()
            
            metadata_phrases = [
                "this table contains",
                "not all combinations",
                "no longer being released",
                "data described by",
                "dimensions",
                "this dataset",
                "contains series",
            ]
            
            if any(phrase in sample_content for phrase in metadata_phrases):
                logger.error(f"❌ DATA IS METADATA - Dataset contains descriptions, not numbers!")
                logger.error(f"   Sample: {str(best_data['data'][0])[:100]}")
                return AuditResult(False, error="Dataset contains metadata descriptions, not actual data. Please query for more recent datasets with current numbers.")
            
            logger.info(f"✅ Data validated - contains actual values, not metadata")
            logger.info(f"\n📝 STEP 3: Preparing REAL DATA for LLM")
            logger.info(f"   Dataset: {best_dataset['title']}")
            logger.info(f"   Rows: {best_data['row_count']}")
            logger.info(f"   Columns: {len(best_data['columns'])} (all kept)")
            
            # Format data as readable text - KEEP ALL COLUMNS
            data_text = f"Dataset: {best_dataset['title']}\n"
            data_text += f"Resource: {best_dataset['resource_name']}\n"
            data_text += f"Columns: {', '.join(best_data['columns'])}\n\n"
            data_text += "Data (first 20 rows):\n"
            
            for row in best_data['data'][:20]:
                data_text += json.dumps(row) + "\n"
            
            logger.debug(f"\n   🔹 REAL DATA WITH ALL COLUMNS:")
            logger.debug(f"   {data_text[:500]}...")

            # STEP 4: LLM analyzes REAL DATA with ALL columns
            analysis_prompt = f"""You are analyzing REAL government data.

User Query: {user_query}

ACTUAL DATA from {best_dataset['title']}:
{data_text}

Analyze this real data and provide:
1. Specific findings with actual numbers from the data
2. Trends and patterns you observe
3. Comparisons between values
4. Insights based on the data
5. Citation of the data source

Use specific numbers and columns from the data. You have all columns available for analysis."""

            logger.info(f"\n🤖 STEP 4: Sending REAL DATA to LLM")
            logger.info(f"   Data size: {len(data_text)} chars")
            logger.info(f"   Columns sent: {len(best_data['columns'])}")
            
            llm_result = ask_llm(analysis_prompt)
            
            if not llm_result.success:
                logger.error(f"❌ LLM analysis failed")
                return AuditResult(False, error=llm_result.error)

            logger.info(f"✅ Analysis complete!")
            logger.info(f"   Response: {llm_result.content[:200]}...")
            logger.info(f"\n{'='*80}\n")

            return AuditResult(
                success=True,
                result={
                    "query": user_query,
                    "dataset_title": best_dataset['title'],
                    "resource": best_dataset['resource_name'],
                    "rows_analyzed": best_data['row_count'],
                    "columns_count": len(best_data['columns']),
                    "relevance": best_data['relevance_score'],
                    "analysis": llm_result.content,
                },
            )

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return AuditResult(False, error=f"Analysis error: {str(e)}")


# Global agent instance
_agent = None


def get_agent() -> APIAgent:
    """Get or create global agent instance."""
    global _agent
    if _agent is None:
        _agent = APIAgent()
    return _agent