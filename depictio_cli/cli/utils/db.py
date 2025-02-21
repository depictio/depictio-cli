from datetime import datetime
import shutil
import json
from tinydb import TinyDB, Query
from pathlib import Path
from typing import List, Dict

from depictio_cli.logging import logger
from depictio_models.models.base import PyObjectId

# Initialize TinyDB with a default file path
DB_PATH = Path("~/.depictio/depictio_cli_db.json").expanduser()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
db = TinyDB(DB_PATH)

# Table Names
RUNS_TABLE = "runs"
FILES_TABLE = "files"


# Indexes (TinyDB doesn't support real indexes, but we can create query helpers)
FILE_INDEX_FIELDS = ["file_hash", "run_id", "data_collection_id"]
RUN_INDEX_FIELDS = ["status", "workflow_id"]


class DBManager:
    """Main database manager class with batch operations and extended functionalities"""

    # region Core Functions
    @staticmethod
    def upsert_runs_batch(runs_data: List[Dict], update: bool = False):
        """Batch upsert runs with conflict resolution"""
        runs_table = db.table(RUNS_TABLE)
        existing_ids = {run["id"] for run in runs_table.all()}

        updated_runs = []
        inserts = []
        for run in runs_data:
            if run["id"] in existing_ids:
                updated_runs.append(run)
            else:
                inserts.append(run)

        if inserts:
            runs_table.insert_multiple(inserts)
        if update:
            if updated_runs:
                for run in updated_runs:
                    runs_table.update(run, Query().id == run["id"])

    @staticmethod
    def upsert_files_batch(files_data: List[Dict], update: bool = False):
        """Batch upsert files with hash-based conflict detection"""
        files_table = db.table(FILES_TABLE)
        existing_hashes = {doc["file_hash"] for doc in files_table.all()}

        new_files = [f for f in files_data if f["file_hash"] not in existing_hashes]
        updated_files = [f for f in files_data if f["file_hash"] in existing_hashes]

        if new_files:
            files_table.insert_multiple(new_files)
        if update:
            if updated_files:
                for file_data in updated_files:
                    files_table.update(file_data, Query().file_hash == file_data["file_hash"])

    # region Update Operations
    @staticmethod
    def update_file(file_id: str, update_data: Dict):
        """Update a single file's metadata"""
        files_table = db.table(FILES_TABLE)
        files_table.update(update_data, Query().id == file_id)

    @staticmethod
    def update_files_batch(query_condition, update_data: Dict):
        """
        Batch update files matching a query condition
        Example: Update all files from a specific run
        """
        files_table = db.table(FILES_TABLE)
        files_table.update(update_data, query_condition)

    # endregion

    # region Delete Operations
    @staticmethod
    def delete_file(file_id: str):
        """Delete a single file by its ID"""
        files_table = db.table(FILES_TABLE)
        files_table.remove(Query().id == file_id)

    @staticmethod
    def delete_files_by_query(query_condition):
        """
        Delete multiple files using a query condition
        Example: Query().run_id == "run_123"
        """
        files_table = db.table(FILES_TABLE)
        files_table.remove(query_condition)

    @staticmethod
    def delete_files_by_ids(doc_ids: List[int]):
        """Delete multiple files by their database document IDs"""
        files_table = db.table(FILES_TABLE)
        files_table.remove(doc_ids=doc_ids)

    @staticmethod
    def delete_files_batch(file_hashes: List[str]):
        """Batch delete files by their hashes"""
        files_table = db.table(FILES_TABLE)
        files_table.remove(Query().file_hash.one_of(file_hashes))

    # endregion

    # region Query Helpers

    @staticmethod
    def get_all_files() -> List[Dict]:
        """Get all files in the database"""
        return db.table(FILES_TABLE).all()

    @staticmethod
    def get_all_runs() -> List[Dict]:
        """Get all runs in the database"""
        return db.table(RUNS_TABLE).all()

    @staticmethod
    def get_file_by_location(location: str) -> Dict:
        """Get a single file by its location on disk"""
        logger.debug(f"Getting file by location: {location}")

        return db.table(FILES_TABLE).get(Query().file_location == str(location))

    @staticmethod
    def get_files_by_run(run_id: PyObjectId) -> List[Dict]:
        """Get all files associated with a specific run"""
        return db.table(FILES_TABLE).search(Query().run_id == str(run_id))

    @staticmethod
    def get_runs_by_status(status: str) -> List[Dict]:
        """Get runs by their status (e.g., 'pending', 'completed')"""
        return db.table(RUNS_TABLE).search(Query().status == status)

    @staticmethod
    def get_recent_runs(limit: int = 10) -> List[Dict]:
        """Get most recently modified runs"""
        all_runs = sorted(db.table(RUNS_TABLE).all(), key=lambda x: x.get("last_modified", ""), reverse=True)
        return all_runs[:limit]

    @staticmethod
    def get_run_by_location(run_location: str) -> str:
        """Get the run ID by its location on disk"""
        return db.table(RUNS_TABLE).get(Query().run_location == run_location)

    # endregion

    # region Maintenance Utilities
    @staticmethod
    def vacuum():
        """Reclaim storage space by removing deleted documents"""
        db.close()
        db.storage.write(db.storage.read())

    @staticmethod
    def backup_db(backup_path: Path):
        """Create a timestamped backup of the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"depictio_backup_{timestamp}.json"
        shutil.copyfile(DB_PATH, backup_file)
        logger.info(f"Database backup created at: {backup_file}")

    @staticmethod
    def cleanup_old_runs(max_age_days: int = 30):
        """Remove runs older than specified days"""
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        runs_table = db.table(RUNS_TABLE)
        old_runs = runs_table.search(Query().created < cutoff)
        runs_table.remove(doc_ids=[doc.doc_id for doc in old_runs])

    # endregion

    # region Statistics
    @staticmethod
    def get_file_counts() -> Dict[str, int]:
        """Get summary statistics of stored files"""
        files_table = db.table(FILES_TABLE)
        return {"total_files": len(files_table), "by_run": {run["id"]: len(DBManager.get_files_by_run(run["id"])) for run in db.table(RUNS_TABLE).all()}}

    @staticmethod
    def get_db_size() -> int:
        """Get the database file size in bytes"""
        return DB_PATH.stat().st_size

    # endregion

    # region Advanced Operations
    @staticmethod
    def transaction(func):
        """Decorator for transactional operations (TinyDB pseudo-transactions)"""

        def wrapper(*args, **kwargs):
            try:
                db._storage.begin_transaction()
                result = func(*args, **kwargs)
                db._storage.commit_transaction()
                return result
            except Exception as e:
                db._storage.rollback_transaction()
                logger.error(f"Transaction failed: {str(e)}")
                raise

        return wrapper

    @staticmethod
    def export_to_json(output_path: Path):
        """Export entire database to JSON file"""
        data = {RUNS_TABLE: db.table(RUNS_TABLE).all(), FILES_TABLE: db.table(FILES_TABLE).all()}
        output_path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def import_from_json(input_path: Path):
        """Import data from JSON backup"""
        data = json.loads(input_path.read_text())
        DBManager.upsert_runs_batch(data.get(RUNS_TABLE, []))
        DBManager.upsert_files_batch(data.get(FILES_TABLE, []))

    # endregion


def sync_local_and_remote_databases():
    """Sync local and remote databases"""
    # Get all local files
    local_files = DBManager.get_all_files()
    