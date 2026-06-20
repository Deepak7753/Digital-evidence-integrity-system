"""
Database Migration: Add User Approval System
This script adds the approval system fields to the users table.
Run this after updating the model to sync database schema.
"""

from app import create_app
from app.extensions import db
from app.models.user import User

def migrate_add_user_approval():
    """Add approval fields to users table"""
    app = create_app()
    
    with app.app_context():
        # Check if columns exist, if not add them
        inspector = db.inspect(db.engine)
        users_columns = [col['name'] for col in inspector.get_columns('users')]
        
        with db.engine.connect() as connection:
            # Add is_approved column if it doesn't exist
            if 'is_approved' not in users_columns:
                print("Adding 'is_approved' column...")
                connection.execute(db.text("""
                    ALTER TABLE users 
                    ADD COLUMN is_approved BOOLEAN DEFAULT FALSE
                """))
                connection.commit()
                print("✓ Added 'is_approved' column")
            
            # Add approval_status column if it doesn't exist
            if 'approval_status' not in users_columns:
                print("Adding 'approval_status' column...")
                connection.execute(db.text("""
                    ALTER TABLE users 
                    ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending'
                """))
                connection.commit()
                print("✓ Added 'approval_status' column")
            
            # Add approval_date column if it doesn't exist
            if 'approval_date' not in users_columns:
                print("Adding 'approval_date' column...")
                connection.execute(db.text("""
                    ALTER TABLE users 
                    ADD COLUMN approval_date DATETIME NULL
                """))
                connection.commit()
                print("✓ Added 'approval_date' column")
            
            # Add approved_by_id column if it doesn't exist
            if 'approved_by_id' not in users_columns:
                print("Adding 'approved_by_id' column...")
                connection.execute(db.text("""
                    ALTER TABLE users 
                    ADD COLUMN approved_by_id INT NULL,
                    ADD CONSTRAINT fk_users_approver 
                    FOREIGN KEY (approved_by_id) REFERENCES users(id) ON DELETE SET NULL
                """))
                connection.commit()
                print("✓ Added 'approved_by_id' column")
            
            # Add index for approval_status if it doesn't exist
            try:
                connection.execute(db.text("""
                    CREATE INDEX idx_approval_status ON users(approval_status)
                """))
                connection.commit()
                print("✓ Added index on 'approval_status' column")
            except:
                print("ℹ Index on 'approval_status' already exists")
        
        print("\n✅ Database migration completed successfully!")
        print("Note: Existing admin accounts will be auto-approved on next startup.")

if __name__ == '__main__':
    migrate_add_user_approval()
