
# AFRIFLOW/backend/tests/conftest.py : configuration pour les tests

import sys
import os
from pathlib import Path

# Ajoute le dossier parent au PYTHONPATH
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

print(f"🔍 Dossier de base: {BASE_DIR}")
print(f"🔍 Python path: {sys.path[0]}")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

@pytest.fixture(scope="session")
def db_engine():
    """Créer un moteur de base de données pour les tests"""
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Créer une session de base de données pour chaque test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Client de test avec la base de données de test"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()