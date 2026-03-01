"""Database configuration and utilities"""

import os
import json
from typing import Optional, List, Dict
from urllib.parse import quote_plus
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if "sslmode=" not in database_url:
            separator = "&" if "?" in database_url else "?"
            database_url = f"{database_url}{separator}sslmode=require"
        return database_url

    pg_host = os.getenv("PGHOST")
    pg_port = os.getenv("PGPORT", "5432")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_database = os.getenv("PGDATABASE")

    if all([pg_host, pg_user, pg_password, pg_database]):
        encoded_password = quote_plus(pg_password)
        return f"postgresql://{pg_user}:{encoded_password}@{pg_host}:{pg_port}/{pg_database}?sslmode=require"

    if os.getenv("RAILWAY_ENVIRONMENT"):
        raise RuntimeError(
            "Database is not configured in Railway. Set DATABASE_URL from your Railway Postgres service variable reference."
        )

    return "postgresql://postgres:dhwani@localhost:5432/createtech"


def get_db_connection():
    db_url = _build_database_url()
    return psycopg.connect(db_url, row_factory=dict_row)


def init_db():
    """Initialize database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            design_engineer_id INTEGER NOT NULL,
            max_budget DOUBLE PRECISION NOT NULL,
            max_timeline_days INTEGER NOT NULL,
            target_area DOUBLE PRECISION NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (design_engineer_id) REFERENCES users(id)
        )
    """)
    
    # Layouts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layouts (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL,
            design_engineer_id INTEGER NOT NULL,
            area DOUBLE PRECISION NOT NULL,
            cost DOUBLE PRECISION NOT NULL,
            timeline_days INTEGER NOT NULL,
            efficiency DOUBLE PRECISION NOT NULL,
            material_factor DOUBLE PRECISION NOT NULL,
            layout_id TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            approval_status TEXT DEFAULT 'pending',
            name TEXT,
            description TEXT,
            layout_data JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (design_engineer_id) REFERENCES users(id)
        )
    """)
    
    # Issue reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id SERIAL PRIMARY KEY,
            layout_id INTEGER NOT NULL,
            site_engineer_id INTEGER NOT NULL,
            issue_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            affected_area DOUBLE PRECISION NOT NULL,
            deviation_percentage DOUBLE PRECISION NOT NULL,
            status TEXT DEFAULT 'reported',
            recalculation_triggered BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (layout_id) REFERENCES layouts(id),
            FOREIGN KEY (site_engineer_id) REFERENCES users(id)
        )
    """)
    
    # Recalculations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recalculations (
            id SERIAL PRIMARY KEY,
            original_layout_id INTEGER NOT NULL,
            issue_id INTEGER,
            trigger_reason TEXT NOT NULL,
            new_area DOUBLE PRECISION NOT NULL,
            new_cost DOUBLE PRECISION NOT NULL,
            new_timeline_days INTEGER NOT NULL,
            modifications JSONB,
            feasibility_score DOUBLE PRECISION NOT NULL,
            confidence_score DOUBLE PRECISION NOT NULL,
            risk_factors JSONB,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (original_layout_id) REFERENCES layouts(id),
            FOREIGN KEY (issue_id) REFERENCES issues(id)
        )
    """)
    
    # Sensor data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL,
            sensor_id TEXT NOT NULL,
            sensor_type TEXT NOT NULL,
            value DOUBLE PRECISION NOT NULL,
            unit TEXT NOT NULL,
            zone TEXT NOT NULL,
            anomaly_detected BOOLEAN DEFAULT FALSE,
            status TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            layout_id INTEGER,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (from_user_id) REFERENCES users(id),
            FOREIGN KEY (to_user_id) REFERENCES users(id),
            FOREIGN KEY (layout_id) REFERENCES layouts(id)
        )
    """)
    
    # Layout history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS layout_history (
            id SERIAL PRIMARY KEY,
            layout_id INTEGER NOT NULL,
            area DOUBLE PRECISION NOT NULL,
            cost DOUBLE PRECISION NOT NULL,
            timeline_days INTEGER NOT NULL,
            change_reason TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (layout_id) REFERENCES layouts(id)
        )
    """)
    
    conn.commit()
    conn.close()


def dict_from_row(row):
    """Convert a row to dict"""
    if row is None:
        return None
    return dict(row)


# Table-specific helper functions
class UserDB:
    @staticmethod
    def create(email: str, password_hash: str, full_name: str, role: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, full_name, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (email, password_hash, full_name, role)
        )
        conn.commit()
        user_id = cursor.fetchone()["id"]
        conn.close()
        return user_id
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = dict_from_row(cursor.fetchone())
        conn.close()
        return user
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, role, created_at FROM users WHERE id = %s", (user_id,))
        user = dict_from_row(cursor.fetchone())
        conn.close()
        return user


class ProjectDB:
    @staticmethod
    def create(name: str, description: str, design_engineer_id: int, max_budget: float, max_timeline_days: int, target_area: float):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, description, design_engineer_id, max_budget, max_timeline_days, target_area) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (name, description, design_engineer_id, max_budget, max_timeline_days, target_area)
        )
        conn.commit()
        project_id = cursor.fetchone()["id"]
        conn.close()
        return project_id
    
    @staticmethod
    def get_by_id(project_id: int) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        project = dict_from_row(cursor.fetchone())
        conn.close()
        return project
    
    @staticmethod
    def get_by_engineer(engineer_id: int) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE design_engineer_id = %s ORDER BY created_at DESC", (engineer_id,))
        projects = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return projects


class LayoutDB:
    @staticmethod
    def create(project_id: int, design_engineer_id: int, area: float, cost: float, timeline_days: int, efficiency: float, material_factor: float, layout_id: str, name: str = None, description: str = None, layout_data: Dict = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        layout_data_json = json.dumps(layout_data) if layout_data else None
        cursor.execute(
            "INSERT INTO layouts (project_id, design_engineer_id, area, cost, timeline_days, efficiency, material_factor, layout_id, name, description, layout_data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (project_id, design_engineer_id, area, cost, timeline_days, efficiency, material_factor, layout_id, name, description, layout_data_json)
        )
        conn.commit()
        layout_db_id = cursor.fetchone()["id"]
        conn.close()
        return layout_db_id
    
    @staticmethod
    def get_by_id(layout_id: int) -> Optional[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM layouts WHERE id = %s", (layout_id,))
        layout = dict_from_row(cursor.fetchone())
        conn.close()
        return layout
    
    @staticmethod
    def get_by_project(project_id: int) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM layouts WHERE project_id = %s ORDER BY created_at DESC", (project_id,))
        layouts = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return layouts
    
    @staticmethod
    def update_approval(layout_id: int, approval_status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE layouts SET approval_status = %s, updated_at = NOW() WHERE id = %s",
            (approval_status, layout_id)
        )
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_status(layout_id: int, status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE layouts SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, layout_id)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update_layout_data(layout_id: int, layout_data: Dict):
        conn = get_db_connection()
        cursor = conn.cursor()
        layout_data_json = json.dumps(layout_data) if layout_data else None
        cursor.execute(
            "UPDATE layouts SET layout_data = %s, updated_at = NOW() WHERE id = %s",
            (layout_data_json, layout_id)
        )
        conn.commit()
        conn.close()


class IssueDB:
    @staticmethod
    def create(layout_id: int, site_engineer_id: int, issue_type: str, severity: str, description: str, affected_area: float, deviation_percentage: float):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO issues (layout_id, site_engineer_id, issue_type, severity, description, affected_area, deviation_percentage) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (layout_id, site_engineer_id, issue_type, severity, description, affected_area, deviation_percentage)
        )
        conn.commit()
        issue_id = cursor.fetchone()["id"]
        conn.close()
        return issue_id
    
    @staticmethod
    def get_by_layout(layout_id: int) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM issues WHERE layout_id = %s ORDER BY created_at DESC", (layout_id,))
        issues = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return issues
    
    @staticmethod
    def update_status(issue_id: int, status: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE issues SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, issue_id)
        )
        conn.commit()
        conn.close()


