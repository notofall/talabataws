#!/usr/bin/env python3
"""
Test PostgreSQL Connection to PlanetScale
"""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from sqlalchemy import text
from database import postgres_settings, init_postgres_db, engine


async def test_connection():
    """Test the database connection"""
    print("=" * 50)
    print("🔄 Testing PostgreSQL Connection to PlanetScale...")
    print("=" * 50)
    print(f"Host: {postgres_settings.postgres_host}")
    print(f"Port: {postgres_settings.postgres_port}")
    print(f"Database: {postgres_settings.postgres_db}")
    print(f"User: {postgres_settings.postgres_user[:20]}...")
    print("=" * 50)
    
    try:
        # Test basic connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            print(f"✅ Connection test: {row[0]}")
        
        # Initialize tables
        print("\n🔄 Creating database tables...")
        await init_postgres_db()
        
        # Verify tables were created
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            print(f"\n📋 Tables created ({len(tables)}):")
            for table in tables:
                print(f"   - {table[0]}")
        
        print("\n" + "=" * 50)
        print("✅ PostgreSQL connection successful!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
