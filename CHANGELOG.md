Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md

Unreleased セクションは空にしておらず、本リリースを v0.1.0（初回リリース）として記載しています。必要に応じて日付やバージョン名は変更してください。

---
# Changelog

全ての変更はこのファイルで記録します。本ファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の指針に従います。

## [0.1.0] - 2026-03-15
### 追加
- 初回リリース: KabuSys — 日本株自動売買システムのベースパッケージを追加。
  - パッケージのエントリポイント:
    - src/kabusys/__init__.py
      - __version__ = "0.1.0"
      - __all__ = ["data", "strategy", "execution", "monitoring"]
  - モジュール雛形:
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

- 環境設定管理（src/kabusys/config.py）を実装:
  - Settings クラスおよびグローバル settings オブジェクトを提供。以下のプロパティを通じて環境変数にアクセス可能:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN: 必須)
    - kabu_api_password (KABU_API_PASSWORD: 必須)
    - kabu_api_base_url (既定値: "http://localhost:18080/kabusapi")
    - slack_bot_token (SLACK_BOT_TOKEN: 必須)
    - slack_channel_id (SLACK_CHANNEL_ID: 必須)
    - duckdb_path (既定値: "data/kabusys.duckdb")
    - sqlite_path (既定値: "data/monitoring.db")
    - env (KABUSYS_ENV; 有効値: "development", "paper_trading", "live")
    - log_level (LOG_LEVEL; 有効値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    - ヘルパー: is_live, is_paper, is_dev

  - 必須環境変数が未設定の場合、_require() が ValueError を送出し、.env.example を参照するよう促すメッセージを含む。

- .env 自動読み込み機能:
  - プロジェクトルートの検出:
    - __file__ を基準に親ディレクトリを上向き探索し、.git または pyproject.toml を見つけたディレクトリをプロジェクトルートとして認識。
    - プロジェクトルートが見つからない場合は自動読み込みをスキップ（配布後やテスト環境でも安全）。
  - 読み込み順序:
    - OS 環境変数 > .env.local > .env
    - .env の先に .env.local を読み込み（.env.local は override=True のため .env の値を上書きできる）。
  - OS 環境変数の保護:
    - 初期ロード時の os.environ のキー集合を protected として扱い、protected に含まれるキーは .env ファイル読み込み中に上書きされない。
  - 自動ロード無効化フラグ:
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能（テスト用途など）。

- .env パーサの強化:
  - export KEY=val 形式に対応。
  - クォート付き値のサポート（シングル/ダブルクォート）、バックスラッシュによるエスケープ処理。
  - クォート付きの場合、対応する終端クォート以前の全てを値として扱い、その後のインラインコメント等は無視。
  - クォートなし値では、'#' をコメントの開始とみなす条件を厳密化（直前がスペースまたはタブの場合のみコメントと認識）。
  - 無効行（空行、コメント行、キーなしの行等）はスキップ。

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### セキュリティ
- （初版のため該当なし）

---

付記（開発者向け）
- Settings を通じてアプリケーション全体で環境設定にアクセスできます。自動ロードを行わない場合やテストで環境を細かく制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- .env の取り扱いに関する仕様（クォートやエスケープ、コメントの取り扱いなど）は、既存の .env ファイルとの互換性を考慮して実装されていますが、複雑なケースはテストしてから利用してください。
- 必須環境変数が不足した場合は即時 ValueError を発生させるため、起動前に .env または OS 環境の設定を確認してください。