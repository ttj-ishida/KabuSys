CHANGELOG
=========

このプロジェクトは "Keep a Changelog" の慣習に従って変更履歴を管理します。
セマンティックバージョニングを使用しています。  

[Unreleased]
-------------

- （現時点のコードベースでは未リリースの差分はありません）

[0.1.0] - 2026-03-15
-------------------

初回リリース。日本株自動売買システムの骨組みと環境設定周りの実装を追加しました。

Added
- パッケージ初期化
  - パッケージバージョンを設定: kabusys.__version__ == "0.1.0"
  - 主要サブパッケージを公開: data, strategy, execution, monitoring（__all__ に追加）
  - 各サブパッケージのプレースホルダ __init__.py を追加（将来の拡張用）

- 環境変数 / 設定管理モジュール（src/kabusys/config.py）
  - プロジェクトルート自動検出機能を実装
    - 現在のファイル位置から上位ディレクトリを探索し、.git または pyproject.toml を検出してプロジェクトルートを決定
    - プロジェクトルートが見つからない場合は自動ロードをスキップ
  - .env ファイルのロード機構を実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - .env.local は .env の値を上書き（ただし OS にある既存環境変数は保護）
    - OS環境変数があるキーは protected として上書きを防止
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等を想定）
  - .env ファイルパーサを実装（堅牢なパース）
    - "export KEY=val" 形式に対応
    - シングル/ダブルクォートされた値のパースをサポート（バックスラッシュエスケープを考慮）
    - クォートなしの値でのインラインコメント処理: '#' の前が空白かタブの場合にコメントとみなす
    - 空行や '#' で始まる行を無視
    - 不正行は無視して続行
    - .env ファイルの読み込み失敗時は warnings.warn で通知
  - Settings クラスを実装（アプリケーション固有設定をプロパティで取得）
    - J-Quants / kabuステーション / Slack / データベース / システム設定をカバー
    - 必須値チェック: 環境変数が未設定の場合は ValueError を送出するヘルパー関数 _require
    - デフォルト値:
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
      - KABUSYS_ENV: "development"（valid: "development","paper_trading","live"）
      - LOG_LEVEL: "INFO"（valid: "DEBUG","INFO","WARNING","ERROR","CRITICAL"）
    - バリデーション付きプロパティ:
      - jquants_refresh_token -> JQUANTS_REFRESH_TOKEN（必須）
      - kabu_api_password -> KABU_API_PASSWORD（必須）
      - kabu_api_base_url -> KABU_API_BASE_URL（デフォルトあり）
      - slack_bot_token -> SLACK_BOT_TOKEN（必須）
      - slack_channel_id -> SLACK_CHANNEL_ID（必須）
      - duckdb_path -> DUCKDB_PATH（Path オブジェクトを返す）
      - sqlite_path -> SQLITE_PATH（Path オブジェクトを返す）
      - env -> KABUSYS_ENV（値チェック）
      - log_level -> LOG_LEVEL（値チェック）
      - is_live / is_paper / is_dev のブールヘルパー

Changed
- 初回リリースのためなし

Fixed
- 初回リリースのためなし

Security
- 環境変数の自動上書きに関して OS 環境変数を protected として扱うことにより、外部からの意図しない上書きを防止する設計を導入

Notes / 今後の留意点
- Settings の一部プロパティは必須環境変数に依存しており、未設定の場合は ValueError を送出します。デプロイ時には .env を適切に用意してください（.env.example の用意が推奨されます）。
- .env の自動読み込みは開発時に便利ですが、テストやコンテナ環境などでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます。
- 今後のリリースでは、各サブパッケージ（data/strategy/execution/monitoring）の具体的実装と API、監視・実行ロジックの追加、テストカバレッジの強化を予定しています。

--- 
（この CHANGELOG はリポジトリ上の現行コードから推測して作成しています。実際の変更履歴や日付はリリース時に適宜調整してください。）