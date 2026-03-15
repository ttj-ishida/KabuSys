# Changelog

すべての注目すべき変更を記録します。本ドキュメントは Keep a Changelog に準拠しており、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-15
初回リリース。

### 追加
- パッケージの初期モジュール構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（各サブパッケージは初期プレースホルダ）
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境変数・設定管理機能を追加（src/kabusys/config.py）
  - .env ファイル（および .env.local）から設定を読み込む自動ローダーを実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env(.local)で上書きされない仕組みを導入
    - プロジェクトルートの検出: 現在のファイル位置から上位ディレクトリを探索し、.git または pyproject.toml を基準にプロジェクトルートを特定（CWD に依存しない実装）
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途など）
  - .env パースの堅牢化
    - コメント行と空行を無視
    - "export KEY=val" 形式に対応
    - シングル／ダブルクォートで囲まれた値の解析（バックスラッシュエスケープを解釈し、閉じクォート以降は無視）
    - クォートなし値のインラインコメント処理: '#' が前に空白/タブを伴う場合のみコメントとして扱う
  - .env ファイル読み込み時の挙動
    - ファイルオープンに失敗した場合は警告を出力してスキップ（warnings.warn）
    - override フラグにより既存環境変数の上書き制御を実装（.env は override=False、.env.local は override=True を使用）
  - 必須環境変数取得ヘルパー _require を実装。未設定時は ValueError を送出（エラーメッセージは .env.example の作成を促す案内を含む）
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で提供
    - J-Quants API: jquants_refresh_token（必須）
    - kabuステーション API: kabu_api_password（必須）、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須）、slack_channel_id（必須）
    - データベースパス:
      - duckdb_path（デフォルト: data/kabusys.duckdb）
      - sqlite_path（デフォルト: data/monitoring.db）
    - システム設定:
      - env（環境）: KABUSYS_ENV を読み取り、許容値は development / paper_trading / live（不正値は ValueError）
      - log_level: LOG_LEVEL を読み取り、許容値は DEBUG/INFO/WARNING/ERROR/CRITICAL（不正値は ValueError）
      - is_live / is_paper / is_dev の便利プロパティを提供
  - settings = Settings() のインスタンスをモジュールレベルで公開（簡単に利用可能）

### 変更
- 該当なし（初回リリース）

### 修正
- 該当なし（初回リリース）

### 削除
- 該当なし（初回リリース）

### セキュリティ
- 該当なし（初回リリース）

補足:
- .env の読み込みはプロジェクトルートの検出に依存するため、配布後やテスト時に挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 必須環境変数が未設定の場合は明示的に例外が発生するため、起動時に必要な設定を漏れなく確認してください。