# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、この CHANGELOG はリポジトリ内のコードから推測して作成しています（リリースタグ・コミット履歴がないため初期リリース相当の記載になっています）。

## [0.1.0] - 2026-03-15

### 追加
- 初期パッケージの公開。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ説明（トップレベル docstring）: "KabuSys - 日本株自動売買システム"
  - エクスポート対象 (kabusys.__all__): `data`, `strategy`, `execution`, `monitoring`

- 設定 / 環境変数管理機能（kabusys.config モジュール）を実装。
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機構を実装。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの判定は .git または pyproject.toml を探索して行う（__file__ 基点で探索するため CWD に依存しない）。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - OS 環境変数（既存の os.environ のキー）は保護（protected）され、`.env.local` の override による上書きを抑制できる仕組みを用意。
    - .env ファイル読み込み失敗時は警告を出す（ファイル読み込みで OSError が発生した場合）。
  - .env の行パース機能を実装（_parse_env_line）。
    - 空行や `#` で始まる行を無視。
    - `export KEY=val` 形式に対応。
    - 値のクォート処理:
      - シングル/ダブルクォートをサポートし、バックスラッシュによるエスケープを処理して対応する閉じクォートまでを値として扱う（その後のインラインコメントは無視）。
      - クォート無しの場合は、`#` が直前にスペース・タブを伴う場合のみコメントとして扱う（通常のコメント処理をより厳密に）。
    - 無効行は無視。
  - .env 読み込み関数 `_load_env_file(path, override=False, protected=frozenset())` を実装:
    - override=False: 未設定のキーのみセット
    - override=True: protected に含まれるキーを除き上書き
  - 必須環境変数取得ヘルパー `_require(key)` を実装。未設定時は ValueError を送出。

- Settings クラスの実装（アプリケーション設定のプロパティ群）。
  - J-Quants API:
    - jquants_refresh_token (`JQUANTS_REFRESH_TOKEN`) — 必須
  - kabuステーション API:
    - kabu_api_password (`KABU_API_PASSWORD`) — 必須
    - kabu_api_base_url (`KABU_API_BASE_URL`) — デフォルト: `http://localhost:18080/kabusapi`
  - Slack:
    - slack_bot_token (`SLACK_BOT_TOKEN`) — 必須
    - slack_channel_id (`SLACK_CHANNEL_ID`) — 必須
  - データベース:
    - duckdb_path (`DUCKDB_PATH`) — デフォルト: `data/kabusys.duckdb`（Path を返す）
    - sqlite_path (`SQLITE_PATH`) — デフォルト: `data/monitoring.db`（Path を返す）
  - システム設定:
    - env (`KABUSYS_ENV`) — デフォルト: `development`。許容値: `development`, `paper_trading`, `live`。不正な値で ValueError を送出。
    - log_level (`LOG_LEVEL`) — デフォルト: `INFO`。許容値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。不正な値で ValueError を送出。
    - is_live / is_paper / is_dev のブールプロパティを提供（env に基づく判定）。
  - モジュール外から利用しやすい singleton インスタンス: `settings = Settings()`

- パッケージ骨格（空の __init__）を配置。
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py

### 変更
- 該当なし（初期リリース）。

### 修正
- 該当なし（初期リリース）。

### 破壊的変更
- 該当なし（初期リリース）。

### セキュリティ
- 該当なし（初期リリース）。

---

注: この CHANGELOG はリポジトリ内のコード構成・実装から推測して作成しています。実際のコミットメッセージや設計意図に基づく詳細は、今後のコミットやリリースに合わせて更新してください。