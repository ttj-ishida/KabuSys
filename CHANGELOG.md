CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠します。

[0.1.0] - 2026-03-15
-------------------

Added
- 初期リリース。
- パッケージ構成を追加:
  - kabusys（トップレベルパッケージ）
  - サブパッケージ: data, strategy, execution, monitoring（現状は空のモジュール/パッケージとして配置）。
  - パッケージのエクスポート定義を __all__ に追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
- 環境設定管理モジュールを追加（src/kabusys/config.py）:
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に特定し、そこから .env および .env.local を読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用など）。
  - 高度な .env パーサ:
    - 空行や # で始まる行をコメントとして無視。
    - "export KEY=val" 形式に対応。
    - シングル／ダブルクォートで囲まれた値のエスケープ（バックスラッシュ）を正しく処理し、対応する閉じクォートまでを値として扱う。
    - クォート無しの場合、'#' は直前がスペース/タブのときのみコメントとして扱う（インラインコメントの扱いに配慮）。
  - .env 読み込み時の挙動:
    - _load_env_file は override フラグを受け取り、override=False の場合は未設定キーのみを設定、override=True の場合は保護されたキー（起動時の OS 環境変数の集合）を上書きしない。
    - ファイル読み込み失敗時は warnings.warn で警告を出力して読み込みをスキップ。
  - 必須環境変数チェック:
    - _require 関数により必須キー未設定時は ValueError を送出し、.env.example を参照するよう促すメッセージを含む。
  - Settings によるプロパティ（環境変数/デフォルト値）:
    - J-Quants API: jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須。
    - kabuステーション API:
      - kabu_api_password (KABU_API_PASSWORD) — 必須。
      - kabu_api_base_url (KABU_API_BASE_URL) — デフォルト "http://localhost:18080/kabusapi"。
    - Slack:
      - slack_bot_token (SLACK_BOT_TOKEN) — 必須。
      - slack_channel_id (SLACK_CHANNEL_ID) — 必須。
    - データベース:
      - duckdb_path (DUCKDB_PATH) — デフォルト "data/kabusys.duckdb"（Path に展開）。
      - sqlite_path (SQLITE_PATH) — デフォルト "data/monitoring.db"（Path に展開）。
    - システム設定:
      - env (KABUSYS_ENV) — 有効値: "development", "paper_trading", "live"。デフォルト "development"。不正値は ValueError。
      - log_level (LOG_LEVEL) — 有効値: "DEBUG","INFO","WARNING","ERROR","CRITICAL"。デフォルト "INFO"。不正値は ValueError。
      - is_live/is_paper/is_dev のヘルパープロパティを提供（env を元に判定）。
- エラーハンドリングとバリデーション:
  - 必須キー未設定、無効な KABUSYS_ENV/LOG_LEVEL の場合は早期に ValueError を投げ、利用者に明確な原因を示すようにした。
  - .env 読み込み時の IO エラーは警告として通知し、アプリケーションの起動を妨げない設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 補足
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やインストール先のディレクトリ構成により自動検出が行えない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動で環境設定を行ってください。
- .env パーサは一般的なシェル互換の記法を想定しているが、特殊ケースや非標準的な書式には対応しない場合があります。必要に応じて .env の整形を行ってください。