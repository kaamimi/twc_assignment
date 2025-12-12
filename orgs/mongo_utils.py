from pymongo import MongoClient
from django.conf import settings


class MongoDBManager:
    """Handle dynamic MongoDB collection operations"""
    
    def __init__(self):
        self.client = MongoClient('localhost', 27017)
        self.db = self.client['master_db']
    
    def create_organization_collection(self, organization_name):
        """Create a new collection for an organization"""
        collection_name = f"org_{organization_name.lower().replace(' ', '_')}"
        
        # Check if collection already exists
        if collection_name in self.db.list_collection_names():
            raise ValueError(f"Collection {collection_name} already exists")
        
        # Create collection with basic schema validation
        self.db.create_collection(collection_name)
        
        # Initialize with a basic document (optional)
        collection = self.db[collection_name]
        collection.insert_one({
            'initialized': True,
            'organization_name': organization_name
        })
        
        return collection_name
    
    def rename_organization_collection(self, old_name, new_name):
        """Rename an organization collection and migrate data"""
        old_collection_name = f"org_{old_name.lower().replace(' ', '_')}"
        new_collection_name = f"org_{new_name.lower().replace(' ', '_')}"
        
        if old_collection_name not in self.db.list_collection_names():
            raise ValueError(f"Collection {old_collection_name} does not exist")
        
        if new_collection_name in self.db.list_collection_names():
            raise ValueError(f"Collection {new_collection_name} already exists")
        
        # Rename the collection
        self.db[old_collection_name].rename(new_collection_name)
        
        return new_collection_name
    
    def delete_organization_collection(self, organization_name):
        """Delete an organization's collection"""
        collection_name = f"org_{organization_name.lower().replace(' ', '_')}"
        
        if collection_name in self.db.list_collection_names():
            self.db[collection_name].drop()
            return True
        return False
    
    def get_collection(self, collection_name):
        """Get a specific collection"""
        return self.db[collection_name]
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()