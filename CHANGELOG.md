# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を採用します。

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: KabuSys — 日本株自動売買システムの基礎パッケージを追加。
  - パッケージ名: `kabusys`
  - パッケージバージョン: `0.1.0`
  - モジュール公開: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - 空のサブパッケージ雛形を含む:
    - `kabusys.data`
    - `kabusys.strategy`
    - `kabusys.execution`
    - `kabusys.monitoring`

- 環境変数/設定管理モジュールを追加 (`kabusys.config`)。
  - プロジェクトルート検出:
    - 現在ファイル位置（__file__）を起点に親ディレクトリを探索し、`.git` または `pyproject.toml` を見つけてプロジェクトルートを特定。
    - CWD に依存しない実装のため、パッケージ配布後の動作も想定。
    - ルートが見つからない場合は自動ロードをスキップ。
  - .env ファイル自動読み込み:
    - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`
    - OS 環境変数のキーは保護（protected）し、`.env` の上書きを防止。
    - `.env` 読み込みの自動無効化オプション: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで自動ロードを無効化可能（テスト用途等）。
    - `.env` ファイル読み込み時にファイルオープンに失敗した場合は警告を発行（例外非発生）。
  - 高度な .env 行パーサー実装:
    - `export KEY=val` フォーマットをサポート。
    - クォートあり（シングル/ダブル）値の処理:
      - バックスラッシュによるエスケープを解釈して対応する閉じクォートまで正しく抽出。
      - クォート内の以降の内容（インラインコメント等）は無視。
    - クォートなし値の処理:
      - `#` をコメントとみなすのは、その `#` の直前がスペースまたはタブの場合のみ（`VALUE#notcomment` のような値を誤って切らない）。
    - 無効行（空行、コメント行、`KEY=（区切りなし）` など）は無視。
  - 環境変数設定ロジック:
    - `_load_env_file(path, override=False, protected=frozenset())` により、`override` フラグと `protected` セットを使った安全な上書き制御を実装。
    - OS 環境変数は読み込み時に保護される（上書きされない）。
  - 必須環境変数取得ヘルパー:
    - `_require(key)` により、未設定時は `ValueError` を送出し、ユーザーに `.env.example` を参考にするよう促すメッセージを含む。

  - Settings クラス（アプリケーション設定）:
    - プロパティで環境変数をラップし、デフォルト値やバリデーションを適用。
    - サポートする設定（主なもの）:
      - J-Quants API:
        - `jquants_refresh_token` → 必須: `JQUANTS_REFRESH_TOKEN`
      - kabuステーション API:
        - `kabu_api_password` → 必須: `KABU_API_PASSWORD`
        - `kabu_api_base_url` → 任意、デフォルト: `http://localhost:18080/kabusapi`
      - Slack:
        - `slack_bot_token` → 必須: `SLACK_BOT_TOKEN`
        - `slack_channel_id` → 必須: `SLACK_CHANNEL_ID`
      - データベース:
        - `duckdb_path` → デフォルト: `data/kabusys.duckdb`（Path オブジェクトとして返す）
        - `sqlite_path` → デフォルト: `data/monitoring.db`（Path オブジェクトとして返す）
      - システム設定:
        - `env` → `KABUSYS_ENV` を小文字化して取得。許容値は `development`, `paper_trading`, `live`。不正値は `ValueError`。
        - `log_level` → `LOG_LEVEL` を大文字化して取得。許容値は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。不正値は `ValueError`。
        - ブールヘルパー: `is_live`, `is_paper`, `is_dev` を提供。

### 既知の注意点
- 現時点ではサブパッケージは雛形であり、個々の機能（戦略の実装、取引実行ロジック、データ取得、監視）は今後実装予定。
- 自動 .env 読み込みはプロジェクトルートが検出できない場合は実行されません。パッケージ化や実行環境に応じて .env の配置に注意してください。

---

今後のリリースでは、具体的な取引戦略、データ取得モジュール、取引実行の統合、監視/通知機能（Slack連携の実装詳細）などを追加していく予定です。