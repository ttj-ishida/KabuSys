Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に準拠します。

フォーマット
----------
各リリースは日付とバージョンで記載しています。カテゴリは主に以下を使用します: Added, Changed, Fixed, Security, Removed, Deprecated, Breaking Changes。

Unreleased
----------
- なし

[0.1.0] - 2026-03-15
--------------------

Added
- 初期リリース。
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py）。
    - __version__ = "0.1.0"
    - __all__ に "data", "strategy", "execution", "monitoring" を公開。
  - サブパッケージのプレースホルダを追加（src/kabusys/{data,strategy,execution,monitoring}/__init__.py）。
- 環境変数 / 設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む機能を実装。
  - プロジェクトルート自動検出
    - 現在ファイル位置を起点に親ディレクトリを走査し、.git または pyproject.toml を見つけた場所をプロジェクトルートとして扱う（_find_project_root）。
    - パッケージ配布後も現在ファイル位置を基準に探索するため、カレントワーキングディレクトリに依存しない実装。
  - .env パーサーを実装（_parse_env_line）
    - 空行やコメント行（#）のスキップ。
    - "export KEY=val" 形式に対応。
    - クォートを含む値の解析（シングル/ダブルクォート、バックスラッシュによるエスケープ対応）。クォートありの場合は対応する閉じクォートまでを値として扱い、その後のインラインコメントは無視。
    - クォートなしの場合は、'#' の直前がスペース/タブであれば以降をコメントとして扱う。
  - .env 読み込みロジック（_load_env_file）
    - ファイルが存在しない場合は無視。
    - ファイルオープン失敗時は警告を出力して読み込みをスキップ。
    - override フラグにより既存の環境変数を上書きするかを制御。
    - protected（frozenset）を指定して上書き禁止するキーを保護（OS 環境変数等の保護に利用）。
  - 自動ロードの挙動
    - 読み込み優先度は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動ロードを無効化可能（テスト等で利用）。
    - プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 必須/検証付き設定取得ヘルパー
    - _require(key) により必須環境変数の取得。未設定時は ValueError を送出。
    - Settings クラスを用意し、プロパティ経由で各種設定にアクセス可能にした（settings = Settings()）。
      - J-Quants API: jquants_refresh_token（JQUANTS_REFRESH_TOKEN を必須）
      - kabuステーション API:
        - kabu_api_password（KABU_API_PASSWORD を必須）
        - kabu_api_base_url（デフォルト: "http://localhost:18080/kabusapi"）
      - Slack:
        - slack_bot_token（SLACK_BOT_TOKEN を必須）
        - slack_channel_id（SLACK_CHANNEL_ID を必須）
      - データベース:
        - duckdb_path（デフォルト: data/kabusys.duckdb、Path を返す）
        - sqlite_path（デフォルト: data/monitoring.db、Path を返す）
      - システム設定:
        - env（KABUSYS_ENV、デフォルト "development"。許可値: "development", "paper_trading", "live"。無効値は ValueError）
        - log_level（LOG_LEVEL、デフォルト "INFO"。有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。無効値は ValueError）
        - is_live / is_paper / is_dev の便宜プロパティを提供
  - ドキュメント的補助
    - config モジュール冒頭に使用例を記載（from kabusys.config import settings ...）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- .env 読み込み時に protected キーセットを導入し、OS 環境変数などの上書きを防止する仕組みを実装。これにより外部 .env ファイルによる既存の安全な環境変数の誤上書きを回避。

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（初回リリース）

注意事項 / 補足
- 必須の環境変数が未設定の場合、Settings の該当プロパティは ValueError を送出します。実行前に .env を用意するか OS 環境変数を設定してください。
- .env のパース実装は一般的なケースに対応していますが、特殊なエスケープや複雑なシェル展開（変数展開やコマンド代入など）はサポートしていません。
- 自動ロードをテストで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 将来的にサブパッケージ（data/strategy/execution/monitoring）に具体的な実装を追加する予定です。