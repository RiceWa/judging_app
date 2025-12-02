import hashlib
import os
from typing import Any, Dict, Optional

import streamlit as st
from bson import ObjectId
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError
from bson.binary import Binary
from datetime import datetime

# Pull from Streamlit secrets first, env var second, and finally a hard-coded fallback
DEFAULT_MONGODB_URI = (
    "mongodb+srv://jamesfitze007_db_user:jwwH5fRMBKM481WK"
    "@judging-app-cluster.snhtcji.mongodb.net/?appName=Judging-app-cluster"
)
DEFAULT_DB_NAME = "judging_app"


def _get_mongo_uri() -> str:
    # Streamlit Cloud exposes secrets via st.secrets
    try:
        secret_uri = st.secrets.get("MONGODB_URI")  # type: ignore[attr-defined]
    except Exception:
        secret_uri = None
    if secret_uri:
        return secret_uri
    return os.getenv("MONGODB_URI", DEFAULT_MONGODB_URI)


def _get_db_name() -> str:
    try:
        secret_db = st.secrets.get("MONGODB_DB")  # type: ignore[attr-defined]
    except Exception:
        secret_db = None
    if secret_db:
        return secret_db
    return os.getenv("MONGODB_DB", os.getenv("MONGODB_DBNAME", DEFAULT_DB_NAME))


@st.cache_resource
def get_db():
    # Cached Mongo client/db for Streamlit reruns
    client = MongoClient(_get_mongo_uri())
    return client[_get_db_name()]


def _oid(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    return ObjectId(str(value))


def _doc_with_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    clean = dict(doc)
    clean["id"] = str(clean.pop("_id"))
    # Normalize nested ids if present
    for key in ("judge_id", "competitor_id", "question_id"):
        if key in clean and isinstance(clean[key], ObjectId):
            clean[key] = str(clean[key])
    return clean


def init_db():
    """
    Create indexes and seed default admin.
    """
    db = get_db()
    db.judges.create_index("email", unique=True)
    db.users.create_index("username", unique=True)
    db.users.create_index("judge_id", unique=True, sparse=True)
    db.scores.create_index(
        [("judge_id", ASCENDING), ("competitor_id", ASCENDING)], unique=True
    )
    db.answers.create_index(
        [("judge_id", ASCENDING), ("competitor_id", ASCENDING), ("question_id", ASCENDING)],
        unique=True,
    )
    create_default_admin_if_missing(db)


# --- CRUD operations ---

def get_judges():
    db = get_db()
    rows = db.judges.find().sort("_id", ASCENDING)
    return [_doc_with_id(r) for r in rows]


def get_judges_with_user():
    db = get_db()
    results = []
    for judge in db.judges.find().sort("_id", ASCENDING):
        linked_user = db.users.find_one({"judge_id": judge["_id"], "role": "judge"})
        merged = _doc_with_id(judge)
        merged["username"] = linked_user["username"] if linked_user else None
        results.append(merged)
    return results


def insert_judge(name: str, email: str):
    db = get_db()
    db.judges.insert_one({"name": name, "email": email})


def create_judge_account(name: str, email: str, username: str, password: str):
    """
    Create judge record and associated user account.
    """
    db = get_db()
    result = db.judges.insert_one({"name": name, "email": email})
    judge_id = result.inserted_id
    try:
        db.users.insert_one(
            {
                "username": username,
                "password_hash": hash_password(password),
                "role": "judge",
                "judge_id": judge_id,
            }
        )
    except DuplicateKeyError:
        # Roll back the judge if username or email collides
        db.judges.delete_one({"_id": judge_id})
        raise
    return judge_id


def get_judge_by_id(judge_id: Any):
    db = get_db()
    row = db.judges.find_one({"_id": _oid(judge_id)})
    return _doc_with_id(row)


def update_judge_account(
    judge_id: Any, name: str, email: str, username: str, password: Optional[str] = None
):
    db = get_db()
    judge_oid = _oid(judge_id)
    db.judges.update_one({"_id": judge_oid}, {"$set": {"name": name, "email": email}})
    update_fields: Dict[str, Any] = {"username": username}
    if password:
        update_fields["password_hash"] = hash_password(password)
    db.users.update_one(
        {"judge_id": judge_oid, "role": "judge"},
        {"$set": update_fields},
        upsert=True,
    )


def delete_judge_account(judge_id: Any):
    db = get_db()
    judge_oid = _oid(judge_id)
    db.scores.delete_many({"judge_id": judge_oid})
    db.answers.delete_many({"judge_id": judge_oid})
    db.users.delete_many({"judge_id": judge_oid})
    db.judges.delete_one({"_id": judge_oid})


def get_competitors():
    db = get_db()
    rows = db.competitors.find().sort("_id", ASCENDING)
    return [_doc_with_id(r) for r in rows]


def insert_competitor(name: str, notes: str = ""):
    db = get_db()
    db.competitors.insert_one({"name": name, "notes": notes})


def update_competitor(competitor_id: Any, name: str, notes: Optional[str] = None):
    db = get_db()
    update_fields: Dict[str, Any] = {"name": name}
    if notes is not None:
        update_fields["notes"] = notes
    db.competitors.update_one({"_id": _oid(competitor_id)}, {"$set": update_fields})

def delete_competitor(competitor_id: Any):
    db = get_db()
    comp_oid = _oid(competitor_id)
    db.scores.delete_many({"competitor_id": comp_oid})
    db.answers.delete_many({"competitor_id": comp_oid})
    db.competitors.delete_one({"_id": comp_oid})


def replace_scores_for_judge(judge_id, scores_dict):
    # Replace all scores for a judge
    db = get_db()
    judge_oid = _oid(judge_id)
    db.scores.delete_many({"judge_id": judge_oid})
    for competitor_id, value in scores_dict.items():
        db.scores.insert_one(
            {"judge_id": judge_oid, "competitor_id": _oid(competitor_id), "value": value}
        )


def save_answers_for_judge(judge_id: Any, competitor_id: Any, answers_dict: Dict[Any, float]):
    # Save per-question answers and aggregate into scores collection
    db = get_db()
    judge_oid = _oid(judge_id)
    comp_oid = _oid(competitor_id)

    db.answers.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})
    db.scores.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})

    if answers_dict:
        payload = []
        for question_id, value in answers_dict.items():
            payload.append(
                {
                    "judge_id": judge_oid,
                    "competitor_id": comp_oid,
                    "question_id": _oid(question_id),
                    "value": value,
                }
            )
        if payload:
            db.answers.insert_many(payload)

        avg_value = sum(answers_dict.values()) / len(answers_dict)
        db.scores.insert_one(
            {"judge_id": judge_oid, "competitor_id": comp_oid, "value": avg_value}
        )
    else:
        # No answers, ensure scores entry is removed
        db.scores.delete_many({"judge_id": judge_oid, "competitor_id": comp_oid})


def get_scores_for_judge(judge_id: Any):
    db = get_db()
    judge_oid = _oid(judge_id)
    rows = db.scores.find({"judge_id": judge_oid})
    return {str(row["competitor_id"]): row["value"] for row in rows}


def get_leaderboard():
    db = get_db()
    pipeline = [
        {
            "$lookup": {
                "from": "scores",
                "localField": "_id",
                "foreignField": "competitor_id",
                "as": "score_docs",
            }
        },
        {
            "$addFields": {
                "num_scores": {"$size": "$score_docs"},
                "total_score": {"$sum": "$score_docs.value"},
                "avg_score": {
                    "$cond": [
                        {"$gt": [{"$size": "$score_docs"}, 0]},
                        {"$avg": "$score_docs.value"},
                        0,
                    ]
                },
            }
        },
        {
            "$project": {
                "name": 1,
                "num_scores": 1,
                "total_score": 1,
                "avg_score": 1,
            }
        },
        {"$sort": {"avg_score": -1}},
    ]
    rows = db.competitors.aggregate(pipeline)
    results = []
    for row in rows:
        base = _doc_with_id(row)
        base["competitor_id"] = base.pop("id")
        base["competitor_name"] = row["name"]
        results.append(base)
    return results


# --- Assets / customization helpers ---
def save_banner_image(file_bytes: bytes, filename: str, content_type: str):
    """Save or replace the banner image in the `assets` collection."""
    db = get_db()
    doc = {
        "key": "banner",
        "filename": filename,
        "content_type": content_type,
        "data": Binary(file_bytes),
        "updated_at": datetime.utcnow(),
    }
    db.assets.update_one({"key": "banner"}, {"$set": doc}, upsert=True)


def get_banner_image():
    """Return banner image as dict or None: {filename, content_type, data(bytes)}"""
    db = get_db()
    row = db.assets.find_one({"key": "banner"})
    if not row:
        return None
    return {
        "filename": row.get("filename"),
        "content_type": row.get("content_type"),
        "data": bytes(row.get("data")) if row.get("data") is not None else None,
        "updated_at": row.get("updated_at"),
    }


def delete_banner_image():
    """Remove the banner image document from the assets collection."""
    db = get_db()
    db.assets.delete_many({"key": "banner"})


# --- Questions/answers ---

def _recompute_scores_from_answers(db):
    """
    Rebuild scores collection by averaging existing answers per judge+competitor.
    """
    db.scores.delete_many({})
    pipeline = [
        {
            "$group": {
                "_id": {"judge_id": "$judge_id", "competitor_id": "$competitor_id"},
                "avg_value": {"$avg": "$value"},
            }
        }
    ]
    docs = []
    for row in db.answers.aggregate(pipeline):
        docs.append(
            {
                "judge_id": row["_id"]["judge_id"],
                "competitor_id": row["_id"]["competitor_id"],
                "value": row["avg_value"],
            }
        )
    if docs:
        db.scores.insert_many(docs)

def get_questions():
    db = get_db()
    rows = db.questions.find().sort("_id", ASCENDING)
    return [_doc_with_id(r) for r in rows]

def insert_question(prompt):
    db = get_db()
    db.questions.insert_one({"prompt": prompt})

def update_question(question_id, prompt):
    db = get_db()
    db.questions.update_one({"_id": _oid(question_id)}, {"$set": {"prompt": prompt}})

def delete_question(question_id):
    db = get_db()
    question_oid = _oid(question_id)
    db.answers.delete_many({"question_id": question_oid})
    db.questions.delete_one({"_id": question_oid})
    _recompute_scores_from_answers(db)

def get_answers_for_judge_competitor(judge_id, competitor_id):
    db = get_db()
    rows = db.answers.find(
        {"judge_id": _oid(judge_id), "competitor_id": _oid(competitor_id)}
    )
    return {str(row["question_id"]): row["value"] for row in rows}


# --- Auth helpers ---

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_default_admin_if_missing(db):
    existing = db.users.count_documents({"role": "admin"})
    if existing == 0:
        db.users.insert_one(
            {"username": "admin", "password_hash": hash_password("admin"), "role": "admin"}
        )

def authenticate_user(username, password):
    db = get_db()
    row = db.users.find_one({"username": username})
    if row and row["password_hash"] == hash_password(password):
        result = _doc_with_id(row)
        return result
    return None
