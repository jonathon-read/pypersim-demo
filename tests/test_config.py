

from pypersim_demo.config import Settings


def test_sqlite_path_default():
    s = Settings()
    assert s.sqlite_path == s.data_dir / "db.sqlite"


def test_lance_dir_default():
    s = Settings()
    assert s.lance_dir == s.data_dir / "lance"


def test_computed_fields_update_with_custom_data_dir(tmp_path):
    s = Settings(data_dir=tmp_path)
    assert s.sqlite_path == tmp_path / "db.sqlite"
    assert s.lance_dir == tmp_path / "lance"


def test_env_var_overrides_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PYPERSIM_DEMO_DATA_DIR", str(tmp_path))
    s = Settings()
    assert s.data_dir == tmp_path


def test_ensure_dirs_exist_creates_directories(tmp_path):
    s = Settings(data_dir=tmp_path / "new_dir")
    assert not s.data_dir.exists()
    s.ensure_dirs_exist()
    assert s.data_dir.exists()
    assert s.lance_dir.exists()


def test_ensure_dirs_exist_is_idempotent(tmp_path):
    s = Settings(data_dir=tmp_path)
    s.ensure_dirs_exist()
    s.ensure_dirs_exist()  # should not raise
    assert s.data_dir.exists()
