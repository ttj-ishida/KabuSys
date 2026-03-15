# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-15

### 追加
- 初期リリース: パッケージ `kabusys` バージョン 0.1.0 を追加。
  - パッケージのトップレベルでのエクスポート: `data`, `strategy`, `execution`, `monitoring`（各サブパッケージは初期スタブとして配置）。
- 環境変数・設定管理モジュール (`kabusys.config`) を実装。
  - プロジェクトルート検出:
    - カレントワーキングディレクトリに依存せず、`__file__` を起点に親ディレクトリを探索して `.git` または `pyproject.toml` を基準にプロジェクトルートを特定。
    - ルートが特定できない場合は自動ロードをスキップ。
  - 自動 .env 読み込み:
    - 読み込み順は OS 環境変数 > `.env.local` > `.env`（`.env.local` は上書き許可）。
    - OS 環境変数を保護するため、既存の OS 環境変数は保護セットとして扱い、`.env` / `.env.local` による上書きを制御。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`（テスト等で利用可能）。
  - `.env` パーサの実装（堅牢な構文処理）:
    - 空行・コメント行（`#` で始まる行）を無視。
    - `export KEY=val` 形式に対応。
    - クォートされた値（シングル・ダブル両対応）をサポートし、バックスラッシュによるエスケープを正しく処理。
    - クォートなし値のインラインコメントは「直前がスペース/タブ」の場合のみコメントとみなす処理。
  - `.env` 読み込み関数の挙動:
    - `override=False` の場合は未設定キーのみを設定。
    - `override=True` の場合は protected（OS 環境変数）に含まれるキーを除き上書き。
    - ファイル読み込み失敗時は警告を発行して処理を継続。
- 設定ラッパー `Settings` クラスを実装（`kabusys.config.settings`）。
  - 必須設定を取得する `_require()` を用意し、未設定時は `ValueError` を送出（ユーザーに `.env.example` を参考に `.env` の作成を促すメッセージ）。
  - J-Quants / kabuステーション / Slack / データベース等の設定プロパティを提供:
    - jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
    - kabu_api_password: KABU_API_PASSWORD（必須）
    - kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token: SLACK_BOT_TOKEN（必須）
    - slack_channel_id: SLACK_CHANNEL_ID（必須）
    - duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb、展開済みパスを返す）
    - sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db、展開済みパスを返す）
  - システム設定およびバリデーション:
    - KABUSYS_ENV の許容値: "development", "paper_trading", "live"（不正な値は `ValueError`）
    - LOG_LEVEL の許容値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"（不正な値は `ValueError`、デフォルトは "INFO"）
    - 環境判定用のヘルパープロパティ: `is_live`, `is_paper`, `is_dev`。
- ドキュメント的な使用例をコード内に記載（`from kabusys.config import settings` など）。

### 変更
- 該当なし（初期リリースのため）。

### 修正
- 該当なし（初期リリースのため）。

### セキュリティ
- 該当なし（初期リリースのため）。

注意:
- 必須の環境変数が未設定の場合、実行時に `ValueError` が発生します。CI/デプロイ環境やローカル実行前に `.env`（あるいは環境変数）を適切に設定してください。