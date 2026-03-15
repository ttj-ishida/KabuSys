# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従います。  
<https://keepachangelog.com/ja/1.0.0/>

## [Unreleased]
（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15
初回公開リリース

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - サブパッケージ（プレースホルダ）を追加: data, strategy, execution, monitoring
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供
  - 利用可能な設定項目（プロパティ）を追加
    - J-Quants: jquants_refresh_token（必須）
    - kabuステーションAPI: kabu_api_password（必須）、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須）、slack_channel_id（必須）
    - データベースパス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
    - システム設定: env（KABUSYS_ENV - デフォルト: development）、log_level（LOG_LEVEL - デフォルト: INFO）
    - 補助プロパティ: is_live, is_paper, is_dev（env による判定）
  - 必須環境変数未設定時に ValueError を送出する _require 関数を実装

- .env 自動読み込み機能を実装
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - プロジェクトルートの検出はパッケージファイル位置から探索（.git または pyproject.toml を基準）するため、CWD に依存しない
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - OS 環境変数を protected として .env による上書きを防止

- .env パーサーを実装
  - export KEY=val 形式に対応
  - シングル / ダブルクォートをサポートし、バックスラッシュエスケープを処理
  - クォートなし値では、直前が空白またはタブの '#' を行コメントとして扱う（インラインコメント処理）
  - 無効行（空行、コメント行、キーがない行）は無視

- 入力検証を追加
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ ValueError
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかでなければ ValueError

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### セキュリティ
- .env の自動ロードにおいて既に存在する OS 環境変数は保護され、.env による意図しない上書きを防止する実装を追加

### 既知の制限 / 備考
- サブパッケージ（data, strategy, execution, monitoring）は現時点で初期化ファイルのみが存在し、具体的な実装は未提供
- .env のパースはいくつかの一般的なケースに対応しているが、すべてのシェルの挙動を完全再現するものではない
- 自動ロードはプロジェクトルートが検出できない場合はスキップされる（配布パッケージ環境での挙動に配慮）
- 必須トークン類（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は実行前に設定が必要。未設定の場合は明確なエラーメッセージで失敗する

--- 

上記はソースコードから推測して作成した初期リリースの変更履歴です。実際のリリースノート作成時は、リリース日や追加の変更点・マイグレーション手順などを追記してください。