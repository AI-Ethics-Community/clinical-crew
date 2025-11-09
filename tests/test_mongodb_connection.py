"""
Test MongoDB Atlas connection with SSL/TLS configuration
"""
import asyncio
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config.settings import settings


async def test_connection():
    """Test MongoDB connection with SSL/TLS"""
    print("=" * 80)
    print("Testing MongoDB Atlas Connection")
    print("=" * 80)
    print(f"\n📊 MongoDB URL: {settings.mongodb_url[:50]}...")
    print(f"📊 Database: {settings.mongodb_db_name}")
    print(f"🔐 Using certifi CA bundle: {certifi.where()}")

    try:
        # Create client with SSL configuration (same as app/main.py)
        print("\n🔌 Creating AsyncIOMotorClient with SSL configuration...")
        client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=settings.mongodb_max_connections,
            minPoolSize=settings.mongodb_min_connections,
            tlsCAFile=certifi.where(),  # Use certifi CA bundle for SSL/TLS
            serverSelectionTimeoutMS=30000,  # 30 second timeout
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
        )

        # Get database
        database = client[settings.mongodb_db_name]

        # Test connection by executing a simple command
        print("🧪 Testing connection with ping command...")
        result = await database.command("ping")

        if result.get("ok") == 1.0:
            print("\n✅ SUCCESS! MongoDB connection established successfully")
            print(f"   Response: {result}")

            # Get server info
            print("\n📋 Server Info:")
            server_info = await database.command("buildInfo")
            print(f"   MongoDB Version: {server_info.get('version')}")
            print(f"   OpenSSL Version: {server_info.get('openssl', {}).get('compiled', 'N/A')}")

            # List collections
            print("\n📁 Collections in database:")
            collections = await database.list_collection_names()
            if collections:
                for col in collections:
                    print(f"   - {col}")
            else:
                print("   (No collections yet)")
        else:
            print("\n❌ FAILED! Unexpected response from ping command")
            print(f"   Response: {result}")

        # Close connection
        print("\n🔌 Closing connection...")
        client.close()
        print("✓ Connection closed")

    except Exception as e:
        print("\n❌ ERROR! Failed to connect to MongoDB")
        print(f"\n🔍 Error Type: {type(e).__name__}")
        print(f"🔍 Error Message: {str(e)}")

        # Check if it's SSL-related
        if "SSL" in str(e) or "TLS" in str(e) or "ssl" in str(e).lower():
            print("\n💡 This appears to be an SSL/TLS error")
            print("   Possible causes:")
            print("   1. MongoDB Atlas requires TLS 1.2 or higher")
            print("   2. Firewall blocking outbound connections")
            print("   3. Missing or outdated CA certificates")
            print("   4. MongoDB connection string missing TLS parameters")

        return False

    print("\n" + "=" * 80)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
