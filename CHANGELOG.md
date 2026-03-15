Keep a Changelog
=================

このプロジェクトは「Keep a Changelog」の形式に準拠します。  
変更はセマンティック バージョニングに従います。

Unreleased
---------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-15
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本パッケージを追加
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてパッケージバージョンを `__version__ = "0.1.0"` として定義。
    - パブリックモジュールとして `data`, `strategy`, `execution`, `monitoring` を __all__ に公開（各サブモジュールは現時点でプレースホルダ）。
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
    - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供（インスタンス: `settings`）。
    - 読み込まれる設定例:
      - JQUANTS_REFRESH_TOKEN（J-Quants API 用リフレッシュトークン、必須）
      - KABU_API_PASSWORD（kabuステーション API 用パスワード、必須）
      - KABU_API_BASE_URL（kabu API のベース URL、デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知用、必須）
      - DUCKDB_PATH（データベースパス、デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（監視用 DB パス、デフォルト: data/monitoring.db）
      - KABUSYS_ENV（動作モード: development / paper_trading / live、デフォルト: development）
      - LOG_LEVEL（ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
    - ヘルパー機能
      - _find_project_root(): __file__ の親ディレクトリを辿り .git または pyproject.toml を見てプロジェクトルートを特定（CWD に依存せず配布後も動作）。
      - 自動 .env ロード機構:
        - 読み込み優先順位: OS 環境変数 > .env.local > .env
        - OS 環境変数は保護され、.env ファイルで上書きされない（.env.local は override=True で上書きするが protected のキーは除外）。
        - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化可能（テスト用途など）。
      - _parse_env_line(): .env の 1 行をパースする関数
        - 空行・コメント行（先頭が #）を無視
        - `export KEY=val` 形式に対応
        - 引用符で囲まれた値（' または "）の取り扱い: バックスラッシュエスケープを解釈し、対応する閉じクォートまでを値として扱う。以降のインラインコメントは無視。
        - 引用符なしの値では、直前が空白・タブの `#` はコメントと判定して切り捨て
      - _load_env_file(): .env ファイルを読み込み、override フラグと protected セットを考慮して os.environ を設定。読み込み失敗時は警告を発行。
    - バリデーション
      - KABUSYS_ENV と LOG_LEVEL の値検証を行い、不正値の場合は ValueError を送出。
    - 便利プロパティ
      - is_live / is_paper / is_dev：KABUSYS_ENV に基づく判定メソッド

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注意事項 / マイグレーション
- 自動 .env 読み込みはプロジェクトルートの検出に依存します。パッケージを配布後やテスト環境でプロジェクト構造が変わる場合、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化し、明示的に環境変数を設定してください。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN 等）が未設定の場合は Settings の各プロパティアクセス時に ValueError が発生します。CI/CD や実行環境での設定漏れに注意してください。