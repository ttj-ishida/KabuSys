Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

[Unreleased]
------------

なし

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース。
- パッケージ構成を追加:
  - kabusys パッケージ (バージョン: 0.1.0)
  - サブパッケージ: data, strategy, execution, monitoring を __all__ で公開
- 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)。
  - Settings クラスを提供し、環境変数からアプリケーション設定を取得するプロパティを実装。
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (デフォルト: "http://localhost:18080/kabusapi")
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (デフォルト: "data/kabusys.duckdb", Path 型で返却)
    - SQLITE_PATH (デフォルト: "data/monitoring.db", Path 型で返却)
    - KABUSYS_ENV の検証（許容値: "development", "paper_trading", "live"。不正な値は ValueError）
    - LOG_LEVEL の検証（許容値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"。不正な値は ValueError）
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須環境変数未設定時は _require が ValueError を投げ、.env.example を参考に .env を作成する旨のメッセージを含む。
- .env 自動読み込み機能を実装（パッケージロード時に自動実行。無効化フラグあり）。
  - プロジェクトルート検出: __file__ を基点に親ディレクトリを上へ探索し、.git または pyproject.toml を根拠に判定（CWD に依存しないためパッケージ配布後も安定）。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップ（テスト等で利用可能）。
  - 読み込みの上書き制御:
    - .env は既存の OS 環境変数を上書きしない（override=False）。
    - .env.local は override=True で読み込み、ただしパッケージ起動時に既に存在する OS 環境変数（protected）を上書きしないよう保護。
  - .env 読み込み時のエラーは例外を投げず warnings.warn で警告を出す実装。
- .env パーサを実装（_parse_env_line）。
  - 空行や先頭が "#" の行を無視。
  - "export KEY=val" 形式に対応。
  - クォートされた値に対するバックスラッシュエスケープ処理: 開始クォートに対応する閉じクォートまでを正しく抽出し、エスケープ（\）を処理。
  - クォートなし値では、'#' をコメントの始まりとみなす条件を厳密化（直前がスペースまたはタブの場合のみコメントとする）して、値中の '#' を不適切に切らないよう配慮。
- パッケージの __init__.py を追加し、パッケージ名・バージョン情報 (__version__ = "0.1.0") を定義。

Changed
- 初版につき該当なし。

Fixed
- 初版につき該当なし。

Removed
- 初版につき該当なし。

Security
- 初版につき該当なし。

Notes
- 現在サブパッケージ（data, strategy, execution, monitoring）の __init__ は存在するが、各サブパッケージ内部の実装は本リリース時点では未実装または空の初期ファイルに留まっています。
- .env のパース挙動や自動ロードの仕様は将来的に変更される可能性があります。ユニットテスト等で確実な環境を再現する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。