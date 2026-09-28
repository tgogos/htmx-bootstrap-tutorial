"""
Tests for the items endpoint.

This module contains comprehensive tests for the items API endpoints,
including CRUD operations, pagination, search, and error handling.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


class TestItemsEndpoint:
    """Test class for items endpoint functionality."""

    def test_complete_crud_flow(self, client: TestClient, sample_item_data: dict, sample_item_update_data: dict):
        """
        Test the complete CRUD flow: Create -> Read -> Update -> Read -> Search -> Delete.
        
        This test follows the exact flow you described:
        1. Add an item
        2. Retrieve it
        3. Update it
        4. Retrieve it updated
        5. Search for it
        6. Delete it
        """
        # Step 1: Create an item
        create_response = client.post("/items/", json=sample_item_data)
        assert create_response.status_code == 201
        
        created_item = create_response.json()
        item_id = created_item["id"]
        
        # Verify the created item
        assert created_item["name"] == sample_item_data["name"]
        assert created_item["description"] == sample_item_data["description"]
        assert "created_at" in created_item
        assert "updated_at" in created_item
        
        # Step 2: Retrieve the item
        get_response = client.get(f"/items/{item_id}")
        assert get_response.status_code == 200
        
        retrieved_item = get_response.json()
        assert retrieved_item["id"] == item_id
        assert retrieved_item["name"] == sample_item_data["name"]
        assert retrieved_item["description"] == sample_item_data["description"]
        
        # Step 3: Update the item
        update_response = client.put(f"/items/{item_id}", json=sample_item_update_data)
        assert update_response.status_code == 200
        
        updated_item = update_response.json()
        assert updated_item["id"] == item_id
        assert updated_item["name"] == sample_item_update_data["name"]
        assert updated_item["description"] == sample_item_update_data["description"]
        assert updated_item["updated_at"] != retrieved_item["updated_at"]
        
        # Step 4: Retrieve the updated item
        get_updated_response = client.get(f"/items/{item_id}")
        assert get_updated_response.status_code == 200
        
        retrieved_updated_item = get_updated_response.json()
        assert retrieved_updated_item["name"] == sample_item_update_data["name"]
        assert retrieved_updated_item["description"] == sample_item_update_data["description"]
        
        # Step 5: Search for the item
        search_response = client.get(f"/items/search/?q={sample_item_update_data['name']}")
        assert search_response.status_code == 200
        
        search_results = search_response.json()
        assert search_results["total_count"] >= 1
        assert len(search_results["items"]) >= 1
        
        # Verify the item is in search results
        found_item = next((item for item in search_results["items"] if item["id"] == item_id), None)
        assert found_item is not None
        assert found_item["name"] == sample_item_update_data["name"]
        
        # Step 6: Delete the item
        delete_response = client.delete(f"/items/{item_id}")
        assert delete_response.status_code == 204
        
        # Verify the item is deleted
        get_deleted_response = client.get(f"/items/{item_id}")
        assert get_deleted_response.status_code == 404

    def test_create_item_success(self, client: TestClient):
        """Test successful item creation."""
        item_data = {
            "name": "New Item",
            "description": "A new test item"
        }
        
        response = client.post("/items/", json=item_data)
        assert response.status_code == 201
        
        created_item = response.json()
        assert created_item["name"] == item_data["name"]
        assert created_item["description"] == item_data["description"]
        assert "id" in created_item
        assert "created_at" in created_item
        assert "updated_at" in created_item

    def test_create_item_minimal_data(self, client: TestClient):
        """Test item creation with minimal required data."""
        item_data = {
            "name": "Minimal Item"
        }
        
        response = client.post("/items/", json=item_data)
        assert response.status_code == 201
        
        created_item = response.json()
        assert created_item["name"] == item_data["name"]
        assert created_item["description"] is None

    def test_create_item_validation_errors(self, client: TestClient):
        """Test item creation with validation errors."""
        # Empty name
        response = client.post("/items/", json={"name": ""})
        assert response.status_code == 422
        
        # Missing name
        response = client.post("/items/", json={"description": "No name"})
        assert response.status_code == 422
        
        # Name too long
        response = client.post("/items/", json={"name": "x" * 101})
        assert response.status_code == 422
        
        # Description too long
        response = client.post("/items/", json={"name": "Valid Name", "description": "x" * 501})
        assert response.status_code == 422

    def test_get_item_success(self, client: TestClient, sample_item_data: dict):
        """Test successful item retrieval."""
        # Create an item first
        create_response = client.post("/items/", json=sample_item_data)
        item_id = create_response.json()["id"]
        
        # Retrieve the item
        response = client.get(f"/items/{item_id}")
        assert response.status_code == 200
        
        item = response.json()
        assert item["id"] == item_id
        assert item["name"] == sample_item_data["name"]

    def test_get_item_not_found(self, client: TestClient):
        """Test retrieving a non-existent item."""
        non_existent_id = str(uuid4())
        
        response = client.get(f"/items/{non_existent_id}")
        assert response.status_code == 404
        
        error_detail = response.json()
        assert "not found" in error_detail["detail"].lower()

    def test_get_item_invalid_uuid(self, client: TestClient):
        """Test retrieving an item with invalid UUID format."""
        response = client.get("/items/invalid-uuid")
        assert response.status_code == 422

    def test_update_item_success(self, client: TestClient, sample_item_data: dict):
        """Test successful item update."""
        # Create an item first
        create_response = client.post("/items/", json=sample_item_data)
        item_id = create_response.json()["id"]
        
        # Update the item
        update_data = {
            "name": "Updated Name",
            "description": "Updated description"
        }
        
        response = client.put(f"/items/{item_id}", json=update_data)
        assert response.status_code == 200
        
        updated_item = response.json()
        assert updated_item["id"] == item_id
        assert updated_item["name"] == update_data["name"]
        assert updated_item["description"] == update_data["description"]

    def test_update_item_partial(self, client: TestClient, sample_item_data: dict):
        """Test partial item update (only updating some fields)."""
        # Create an item first
        create_response = client.post("/items/", json=sample_item_data)
        item_id = create_response.json()["id"]
        
        # Update only the name
        update_data = {"name": "Only Name Updated"}
        
        response = client.put(f"/items/{item_id}", json=update_data)
        assert response.status_code == 200
        
        updated_item = response.json()
        assert updated_item["name"] == update_data["name"]
        assert updated_item["description"] == sample_item_data["description"]  # Should remain unchanged

    def test_update_item_not_found(self, client: TestClient):
        """Test updating a non-existent item."""
        non_existent_id = str(uuid4())
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/items/{non_existent_id}", json=update_data)
        assert response.status_code == 404

    def test_update_item_no_fields(self, client: TestClient, sample_item_data: dict):
        """Test updating an item with no fields provided."""
        # Create an item first
        create_response = client.post("/items/", json=sample_item_data)
        item_id = create_response.json()["id"]
        
        # Try to update with empty data
        response = client.put(f"/items/{item_id}", json={})
        assert response.status_code == 400
        
        error_detail = response.json()
        assert "no fields provided" in error_detail["detail"].lower()

    def test_delete_item_success(self, client: TestClient, sample_item_data: dict):
        """Test successful item deletion."""
        # Create an item first
        create_response = client.post("/items/", json=sample_item_data)
        item_id = create_response.json()["id"]
        
        # Delete the item
        response = client.delete(f"/items/{item_id}")
        assert response.status_code == 204
        
        # Verify the item is deleted
        get_response = client.get(f"/items/{item_id}")
        assert get_response.status_code == 404

    def test_delete_item_not_found(self, client: TestClient):
        """Test deleting a non-existent item."""
        non_existent_id = str(uuid4())
        
        response = client.delete(f"/items/{non_existent_id}")
        assert response.status_code == 404

    def test_get_items_pagination(self, client: TestClient):
        """Test items listing with pagination."""
        # Create multiple items
        items_created = []
        for i in range(15):
            item_data = {"name": f"Item {i+1}", "description": f"Description {i+1}"}
            response = client.post("/items/", json=item_data)
            items_created.append(response.json())
        
        # Test first page
        response = client.get("/items/?page=1&size=10")
        assert response.status_code == 200
        
        page1_data = response.json()
        assert len(page1_data["items"]) == 10
        assert page1_data["page"] == 1
        assert page1_data["size"] == 10
        assert page1_data["total_count"] == 15
        assert page1_data["total_pages"] == 2
        
        # Test second page
        response = client.get("/items/?page=2&size=10")
        assert response.status_code == 200
        
        page2_data = response.json()
        assert len(page2_data["items"]) == 5
        assert page2_data["page"] == 2
        assert page2_data["size"] == 10
        assert page2_data["total_count"] == 15
        assert page2_data["total_pages"] == 2

    def test_get_items_default_pagination(self, client: TestClient):
        """Test items listing with default pagination parameters."""
        # Create a few items
        for i in range(5):
            item_data = {"name": f"Default Item {i+1}"}
            client.post("/items/", json=item_data)
        
        response = client.get("/items/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 10
        assert len(data["items"]) == 5

    def test_get_items_pagination_validation(self, client: TestClient):
        """Test pagination parameter validation."""
        # Invalid page number
        response = client.get("/items/?page=0")
        assert response.status_code == 422
        
        # Invalid size
        response = client.get("/items/?size=0")
        assert response.status_code == 422
        
        # Size too large
        response = client.get("/items/?size=101")
        assert response.status_code == 422

    def test_search_items_success(self, client: TestClient):
        """Test successful item search."""
        # Create items with different names
        items_data = [
            {"name": "Apple iPhone", "description": "Smartphone"},
            {"name": "Samsung Galaxy", "description": "Android phone"},
            {"name": "Apple MacBook", "description": "Laptop"},
            {"name": "Dell Laptop", "description": "Windows laptop"}
        ]
        
        created_items = []
        for item_data in items_data:
            response = client.post("/items/", json=item_data)
            created_items.append(response.json())
        
        # Search for "Apple"
        response = client.get("/items/search/?q=Apple")
        assert response.status_code == 200
        
        search_results = response.json()
        assert search_results["total_count"] == 2
        assert len(search_results["items"]) == 2
        
        # Verify the correct items are returned
        item_names = [item["name"] for item in search_results["items"]]
        assert "Apple iPhone" in item_names
        assert "Apple MacBook" in item_names

    def test_search_items_case_insensitive(self, client: TestClient):
        """Test that search is case-insensitive."""
        # Create an item
        item_data = {"name": "Test Item", "description": "A test item"}
        client.post("/items/", json=item_data)
        
        # Search with different cases
        for query in ["test", "TEST", "Test", "tEsT"]:
            response = client.get(f"/items/search/?q={query}")
            assert response.status_code == 200
            
            search_results = response.json()
            assert search_results["total_count"] == 1
            assert search_results["items"][0]["name"] == "Test Item"

    def test_search_items_no_results(self, client: TestClient):
        """Test search with no matching results."""
        # Create an item
        item_data = {"name": "Existing Item"}
        client.post("/items/", json=item_data)
        
        # Search for something that doesn't exist
        response = client.get("/items/search/?q=NonExistent")
        assert response.status_code == 200
        
        search_results = response.json()
        assert search_results["total_count"] == 0
        assert len(search_results["items"]) == 0

    def test_search_items_pagination(self, client: TestClient):
        """Test search with pagination."""
        # Create multiple items with similar names
        for i in range(15):
            item_data = {"name": f"Test Item {i+1}"}
            client.post("/items/", json=item_data)
        
        # Search with pagination
        response = client.get("/items/search/?q=Test&page=1&size=10")
        assert response.status_code == 200
        
        search_results = response.json()
        assert len(search_results["items"]) == 10
        assert search_results["page"] == 1
        assert search_results["size"] == 10
        assert search_results["total_count"] == 15
        assert search_results["total_pages"] == 2

    def test_search_items_validation(self, client: TestClient):
        """Test search parameter validation."""
        # Empty search query
        response = client.get("/items/search/?q=")
        assert response.status_code == 422
        
        # Missing search query
        response = client.get("/items/search/")
        assert response.status_code == 422

    def test_items_storage_isolation(self, client: TestClient):
        """Test that items storage is properly isolated between tests."""
        # This test verifies that the in-memory storage doesn't leak between tests
        response = client.get("/items/")
        assert response.status_code == 200
        
        # Should be empty at the start of each test
        data = response.json()
        assert data["total_count"] == 0
        assert len(data["items"]) == 0
