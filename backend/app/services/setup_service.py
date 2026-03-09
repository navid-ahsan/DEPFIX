"""Setup and onboarding service."""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.models.database import Dependency, SetupStatus, User


# Available dependencies with metadata
AVAILABLE_DEPENDENCIES = {
    "torch": {
        "display_name": "PyTorch",
        "description": "Deep learning framework for Python",
        "category": "ml",
        "homepage": "https://pytorch.org",
        "documentation_url": "https://pytorch.org/docs",
        "repository_url": "https://github.com/pytorch/pytorch",
        "pypi_url": "https://pypi.org/project/torch/",
    },
    "torchvision": {
        "display_name": "TorchVision",
        "description": "Computer vision library for PyTorch",
        "category": "ml",
        "homepage": "https://pytorch.org/vision",
        "documentation_url": "https://pytorch.org/vision/stable/",
        "repository_url": "https://github.com/pytorch/vision",
        "pypi_url": "https://pypi.org/project/torchvision/",
    },
    "torchaudio": {
        "display_name": "TorchAudio",
        "description": "Audio processing library for PyTorch",
        "category": "ml",
        "homepage": "https://pytorch.org/audio",
        "documentation_url": "https://pytorch.org/audio/stable/",
        "repository_url": "https://github.com/pytorch/audio",
        "pypi_url": "https://pypi.org/project/torchaudio/",
    },
    "scikit-learn": {
        "display_name": "Scikit-Learn",
        "description": "Machine learning library for Python",
        "category": "ml",
        "homepage": "https://scikit-learn.org",
        "documentation_url": "https://scikit-learn.org/stable/",
        "repository_url": "https://github.com/scikit-learn/scikit-learn",
        "pypi_url": "https://pypi.org/project/scikit-learn/",
    },
    "monai": {
        "display_name": "MONAI",
        "description": "Medical imaging AI framework",
        "category": "ml",
        "homepage": "https://monai.io",
        "documentation_url": "https://docs.monai.io",
        "repository_url": "https://github.com/Project-MONAI/MONAI",
        "pypi_url": "https://pypi.org/project/monai/",
    },
    "requests": {
        "display_name": "Requests",
        "description": "HTTP library for Python",
        "category": "web",
        "homepage": "https://requests.readthedocs.io",
        "documentation_url": "https://requests.readthedocs.io",
        "repository_url": "https://github.com/psf/requests",
        "pypi_url": "https://pypi.org/project/requests/",
    },
    "pyramid": {
        "display_name": "Pyramid",
        "description": "Web application framework",
        "category": "web",
        "homepage": "https://trypyramid.com",
        "documentation_url": "https://docs.pylonsproject.org/projects/pyramid",
        "repository_url": "https://github.com/Pylons/pyramid",
        "pypi_url": "https://pypi.org/project/pyramid/",
    },
    "waitress": {
        "display_name": "Waitress",
        "description": "Pure Python WSGI server",
        "category": "web",
        "homepage": "https://docs.pylonsproject.org/projects/waitress",
        "documentation_url": "https://docs.pylonsproject.org/projects/waitress",
        "repository_url": "https://github.com/Pylons/waitress",
        "pypi_url": "https://pypi.org/project/waitress/",
    },
    "flower": {
        "display_name": "Flower",
        "description": "Celery task monitoring and management tool",
        "category": "tools",
        "homepage": "https://flower.readthedocs.io",
        "documentation_url": "https://flower.readthedocs.io",
        "repository_url": "https://github.com/mher/flower",
        "pypi_url": "https://pypi.org/project/flower/",
    },
    "tenseal": {
        "display_name": "TenSEAL",
        "description": "Encrypted machine learning library",
        "category": "ml",
        "homepage": "https://github.com/OpenMined/TenSEAL",
        "documentation_url": "https://tenseal.readthedocs.io",
        "repository_url": "https://github.com/OpenMined/TenSEAL",
        "pypi_url": "https://pypi.org/project/tenseal/",
    },
}


def get_or_create_dependencies(db: Session) -> List[Dependency]:
    """Ensure all dependencies exist in database."""
    dependencies = []
    
    for dep_name, metadata in AVAILABLE_DEPENDENCIES.items():
        dep = db.query(Dependency).filter(Dependency.name == dep_name).first()
        
        if not dep:
            dep = Dependency(
                name=dep_name,
                display_name=metadata.get("display_name"),
                description=metadata.get("description"),
                category=metadata.get("category"),
                homepage=metadata.get("homepage"),
                documentation_url=metadata.get("documentation_url"),
                repository_url=metadata.get("repository_url"),
                pypi_url=metadata.get("pypi_url"),
                is_active=True,
            )
            db.add(dep)
        
        dependencies.append(dep)
    
    db.commit()
    return dependencies


def get_available_dependencies(db: Session) -> List[Dict]:
    """Get all available dependencies with metadata."""
    get_or_create_dependencies(db)
    
    deps = db.query(Dependency).filter(Dependency.is_active == True).all()
    
    return [
        {
            "id": dep.id,
            "name": dep.name,
            "display_name": dep.display_name,
            "description": dep.description,
            "category": dep.category,
            "documentation_url": dep.documentation_url,
            "repository_url": dep.repository_url,
        }
        for dep in deps
    ]


def select_dependencies(
    db: Session, user: User, dependency_names: List[str]
) -> SetupStatus:
    """User selects dependencies for Phase 1."""
    
    # Get setup status or create new
    setup = db.query(SetupStatus).filter(SetupStatus.user_id == user.id).first()
    if not setup:
        setup = SetupStatus(user_id=user.id)
        db.add(setup)
    
    # Store selected dependencies
    setup.selected_dependencies = dependency_names
    setup.updated_at = __import__("datetime").datetime.utcnow()
    
    db.commit()
    db.refresh(setup)
    
    return setup


def load_docs_from_local_jsonl(dependency_name: str) -> Optional[Dict]:
    """Load pre-downloaded docs from local jsonl file."""
    jsonl_path = Path(f"/home/navid/project/socialwork/data/documents/{dependency_name}.jsonl")
    
    if not jsonl_path.exists():
        return None
    
    total_chunks = 0
    sample_chunks = []
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    total_chunks += 1
                    if len(sample_chunks) < 5:
                        sample_chunks.append({
                            "text": chunk.get("content") or chunk.get("text", ""),
                            "source": chunk.get("source", ""),
                            "metadata": chunk.get("metadata", {}),
                        })
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error loading {dependency_name}.jsonl: {e}")
        return None
    
    return {
        "dependency": dependency_name,
        "total_chunks": total_chunks,
        "sample_chunks": sample_chunks,
        "ready_for_embedding": True,
    }


def get_setup_status(db: Session, user: User) -> Optional[SetupStatus]:
    """Get user's current setup status."""
    return db.query(SetupStatus).filter(SetupStatus.user_id == user.id).first()


def check_doc_availability(dependency_names: List[str]) -> Dict[str, bool]:
    """Check which dependencies have docs available locally."""
    availability = {}
    
    for dep_name in dependency_names:
        jsonl_path = Path(f"/home/navid/project/socialwork/data/documents/{dep_name}.jsonl")
        availability[dep_name] = jsonl_path.exists()
    
    return availability


def mark_phase1_complete(db: Session, user: User) -> SetupStatus:
    """Mark Phase 1 as complete when doc loading is done."""
    setup = get_setup_status(db, user)
    if setup:
        setup.phase1_completed = True
        setup.updated_at = __import__("datetime").datetime.utcnow()
        db.commit()
        db.refresh(setup)
    
    return setup
