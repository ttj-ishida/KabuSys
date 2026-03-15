# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

全般なルール: セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-15
最初の公開リリース。

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py に __version__ を定義）
  - パッケージ公開インターフェース: __all__ に "data", "strategy", "execution", "monitoring" を設定（各サブパッケージの __init__ はプレースホルダとして追加）。
- 環境変数 / 設定読み込みモジュールを追加（src/kabusys/config.py）
  - プロジェクトルート検出
    - 現在のファイル位置から親ディレクトリを上方向に探索し、.git または pyproject.toml を基準にプロジェクトルートを特定する機能を実装。これによりカレントワーキングディレクトリに依存せずパッケージ配布後も正しく動作するよう設計。
    - プロジェクトルートが見つからない場合、自動ロードをスキップする。
  - .env ファイル自動ロード
    - デフォルトの優先順: OS 環境変数 > .env.local > .env
    - OS 環境変数に存在するキーは保護（protected）され、.env.local の上書き対象から除外される。
    - .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途など）。
  - .env パーサ機能
    - export KEY=val 形式に対応。
    - クォート値（シングル／ダブル）に対応し、バックスラッシュによるエスケープ処理を考慮して正しく閉じクォートを検出・デコード。
    - クォートなし値に対しては、`#` がスペースまたはタブで前置されている場合にのみインラインコメントと見なす（それ以外は値の一部として扱う）。
    - 無効行（空行、コメント行、`=` がない行など）は無視。
    - ファイル読み込みエラー時には警告を発する（例: ファイルアクセス権限等）。
  - .env ロード時の挙動
    - _load_env_file(path, override=False): override=False の場合は未設定のキーのみ環境変数に設定する（既存の OS 環境変数を上書きしない）。
    - _load_env_file(path, override=True): override=True の場合は protected に含まれるキーを除き上書きする（.env.local は override=True でロードされる）。
  - 設定取得用クラス Settings を提供（settings インスタンスをモジュールグローバルに公開）
    - 必須トークン・ID の取得とバリデーション（未設定時は ValueError を送出）
      - JQUANTS_REFRESH_TOKEN -> jquants_refresh_token（必須）
      - KABU_API_PASSWORD -> kabu_api_password（必須）
      - SLACK_BOT_TOKEN -> slack_bot_token（必須）
      - SLACK_CHANNEL_ID -> slack_channel_id（必須）
      - 未設定時のエラーメッセージに .env.example を参照する旨を含める。
    - オプション設定とデフォルト値
      - KABU_API_BASE_URL -> kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH -> duckdb_path（デフォルト: data/kabusys.duckdb、Path オブジェクトで返却）
      - SQLITE_PATH -> sqlite_path（デフォルト: data/monitoring.db、Path オブジェクトで返却）
    - 環境種別とログレベルのバリデーション
      - KABUSYS_ENV の許容値: "development", "paper_trading", "live"（それ以外は ValueError）
      - LOG_LEVEL の許容値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"（大文字化して検証、無効値で ValueError）
    - 利便性プロパティ
      - is_live, is_paper, is_dev を提供（env の値に基づく真偽値）
  - ユーザーが参照しやすい様に settings = Settings() を提供。  

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- なし

補足:
- サブパッケージ (data, strategy, execution, monitoring) は初期スケルトンとして存在。今後ここにデータ取得、取引戦略、注文実行、監視系の実装が追加される想定です。