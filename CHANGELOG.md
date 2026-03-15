# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-15
初回リリース。

### 追加
- パッケージ初期構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（各サブパッケージはプレースホルダとして存在）
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供
  - 自動読み込みの挙動
    - プロジェクトルート判定: __file__ の親ディレクトリを辿り、.git または pyproject.toml を基準にプロジェクトルートを特定（CWD に依存しない）
    - 読み込み順序: OS環境変数 > .env > .env.local（.env.local は上書き）
    - OS環境変数を保護するための protected キー集合を採用し、既存の OS 環境変数を .env によって上書きしない
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

  - .env パーサ実装
    - export KEY=val 形式に対応
    - シングル/ダブルクォートされた値に対するエスケープ（バックスラッシュ）処理と対応する閉じクォートの検出
    - クォートなしの場合、行内コメントの認識ルール（'#' の前の文字が空白またはタブの場合のみコメント扱い）
    - 無効行（空行、コメント行、'key=value' でない行）は無視

  - .env ファイル読み込みの安全処理
    - ファイル読み込み失敗時は warnings.warn で警告を出し、処理を続行

  - 必須変数チェック
    - _require() により必須環境変数が未設定の場合は ValueError を送出

  - Settings による取得可能な設定（プロパティ）
    - J-Quants
      - jquants_refresh_token（必須: JQUANTS_REFRESH_TOKEN）
    - kabu ステーション API
      - kabu_api_password（必須: KABU_API_PASSWORD）
      - kabu_api_base_url（任意: デフォルト "http://localhost:18080/kabusapi"）
    - Slack
      - slack_bot_token（必須: SLACK_BOT_TOKEN）
      - slack_channel_id（必須: SLACK_CHANNEL_ID）
    - データベース
      - duckdb_path（任意: デフォルト "data/kabusys.duckdb"）
      - sqlite_path（任意: デフォルト "data/monitoring.db"）
    - システム設定
      - env（KABUSYS_ENV、デフォルト "development"。有効値: "development", "paper_trading", "live"。不正値は ValueError）
      - log_level（LOG_LEVEL、デフォルト "INFO"。有効値: "DEBUG","INFO","WARNING","ERROR","CRITICAL"。不正値は ValueError）
      - is_live / is_paper / is_dev（env に基づくブール判定の利便性プロパティ）

### 変更
- 該当なし（初回リリース）

### 修正
- 該当なし（初回リリース）

### 削除
- 該当なし（初回リリース）

### セキュリティ
- 該当なし（初回リリース）

---

備考:
- .env のパースと自動ロードの挙動は、配布後に CWD に依存せず正しく動作するよう設計されています。テスト等で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。