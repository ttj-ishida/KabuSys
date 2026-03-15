Keep a Changelogに準拠した形式で、コードベースから推測した変更履歴を以下に記載します（日本語）。

CHANGELOG.md
=============

すべての重要な変更点をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に従います。  

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース。
- パッケージの基本構成を追加:
  - モジュール: `kabusys`（トップレベル）。
  - サブパッケージ（プレースホルダ）: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`。
  - パッケージバージョン: `__version__ = "0.1.0"`。
  - 公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 環境設定読み込みモジュールを追加 (`kabusys.config`):
  - .env ファイルまたは環境変数から設定値を読み込む仕組みを実装。
  - 自動ロードの探索方法:
    - 現在のモジュール位置から親ディレクトリを辿り、プロジェクトルートを特定（.git または pyproject.toml を基準）。  
      └ パッケージ配布後でも動作するよう、カレントワーキングディレクトリ（CWD）に依存しない探索を行う。
  - 自動ロードの振る舞い:
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - `.env.local` は `.env` の値を上書きする（ただし OS 環境変数は保護される）。
    - 自動ロードを無効にするためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサーの強化:
    - `export KEY=val` 形式に対応。
    - クォートされた値に対する扱い:
      - シングル／ダブルクォートをサポートし、バックスラッシュによるエスケープを解釈して対応する閉じクォートまでを正しく抽出する（クォート内の # はコメントとみなさない）。
    - 非クォート値のコメント扱い:
      - `#` が値中に現れた場合、直前の文字がスペースまたはタブの場合のみコメント開始とみなして以降を無視する（そうでない場合は `#` を値の一部とする）。
    - 無効行（空行や `#` で始まる行、`key=value` 形式でない行）は無視する。
    - ファイル読み込み失敗時は警告を出してスキップ。
    - .env 読み込み時に OS 環境変数を保護するための `protected` セットを導入（`.env.local` の上書き時でも OS 環境変数は上書きされない）。
  - 設定用の高レベル API (`Settings` クラス) を提供:
    - 利用例: `from kabusys.config import settings`、`settings.jquants_refresh_token` など。
    - 必須値取得のヘルパー `_require` を実装し、未設定時は `ValueError` を送出。
    - 用意されたプロパティ（環境変数名の説明）:
      - J-Quants 関連:
        - jquants_refresh_token (環境変数: JQUANTS_REFRESH_TOKEN) — 必須
      - kabuステーション API:
        - kabu_api_password (KABU_API_PASSWORD) — 必須
        - kabu_api_base_url (KABU_API_BASE_URL) — デフォルト: "http://localhost:18080/kabusapi"
      - Slack:
        - slack_bot_token (SLACK_BOT_TOKEN) — 必須
        - slack_channel_id (SLACK_CHANNEL_ID) — 必須
      - データベース:
        - duckdb_path (DUCKDB_PATH) — デフォルト: "data/kabusys.duckdb"
        - sqlite_path (SQLITE_PATH) — デフォルト: "data/monitoring.db"
      - システム設定:
        - env (KABUSYS_ENV) — デフォルト: "development"。許容値: "development", "paper_trading", "live"。不正値時は `ValueError`。
        - log_level (LOG_LEVEL) — デフォルト: "INFO"。許容値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"。不正値時は `ValueError`。
        - is_live / is_paper / is_dev のブール判定プロパティを提供。
    - モジュールレベルで `settings = Settings()` を作成し、アプリケーション全体で共有可能にした。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- OS 環境変数を保護する設計を導入（.env の読み込みで OS 環境変数が上書きされないように保護）。

Notes / 利用上の注意
- 自動環境変数読み込みはプロジェクトルートが検出できない場合はスキップされる（配布後や特殊環境での安全策）。
- テストなどで自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定してください。
- .env のパース仕様は一般的なシェルの .env 互換を意識しているが、細かな差異があるため複雑な値はクォートし、必要に応じてエスケープを使用してください。
- 必須環境変数が未設定の場合は `ValueError` が発生するため、実行前に環境を整えてください。

今後の予定（推測）
- subpackages（data/strategy/execution/monitoring）に実際の機能（データ取得、戦略実装、注文実行、監視／通知機能）を追加予定。
- 設定や .env パーサーのユニットテスト強化、ロギングやエラーハンドリングの拡充。