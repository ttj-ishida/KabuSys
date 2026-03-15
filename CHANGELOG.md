# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリースの順は新しいものが上になります。

リンク: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初回公開リリース。主要な機能と初期実装を含みます。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py にて設定）
  - 公開サブパッケージ（__all__）: data, strategy, execution, monitoring（各サブパッケージのプレースホルダを含む）

- 環境設定管理（src/kabusys/config.py）
  - Settings クラスと settings インスタンスを提供。環境変数からアプリケーション設定を取得するプロパティを実装。
  - サポートする設定（主なもの）:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - データベースファイル: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - 実行環境: KABUSYS_ENV（development/paper_trading/live、検証あり）
    - ログレベル: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、検証あり）
  - 補助プロパティ: is_live, is_paper, is_dev

  - .env 自動読み込み機能
    - プロジェクトルートを .git または pyproject.toml を基準に探索し、自動で .env と .env.local を読み込む（プロジェクトルートが見つからない場合はスキップ）。
    - 読み込み順・優先度: OS 環境変数 > .env > .env.local（.env.local は override=True のため .env の値を上書き可能。ただし既存の OS 環境変数は保護される）。
    - 自動読み込みを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パースの実装詳細:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮してクォートを正しく処理
    - クォートなしの場合、'#' はその直前がスペースまたはタブならコメントとして扱う（それ以外は値の一部）
    - 無効行（空行、コメント行、キーがない行）は無視
  - .env ファイル読み込み失敗時は warnings.warn で通知（例外は投げない）

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3層構造を想定したテーブル群を定義（Raw / Processed / Feature / Execution レイヤー）。
  - 主なテーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して主キー・外部キー・CHECK 制約（非負・サイズ制約・列値制約等）を適用
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルを初期化し、全テーブル・インデックスを作成して接続を返す
      - db_path の親ディレクトリが存在しない場合は自動作成
      - ":memory:" を指定してインメモリ DB を使用可能
      - 冪等性あり（既存テーブルはスキップ）
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用すること）

### 改良
- 型ヒント（Python 3.10 以降の表記: Path | None, str | Path など）と詳細な docstring を追加し、可読性・メンテナンス性を向上。
- スキーマ定義をモジュール内の定数文字列として分離し、作成順序と依存関係を明示。

### 修正
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ処理を実装して、複雑な値（改行・特殊文字をエスケープした文字列など）に対応。
  - コメントの解釈を改善して、意図しない '#' を値の一部として扱うケースを回避。

### 注意事項 / マイグレーション
- DuckDB を使う場合、初回は必ず init_schema() を呼び出してスキーマを作成してください。get_connection() は既存スキーマに接続するための関数です。
- 自動で .env を読み込む際に OS 環境変数は保護されます。テスト等で .env の読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV や LOG_LEVEL に無効な値を設定すると ValueError が発生します。利用可能な値はエラーメッセージに含まれます。

---

（以後の変更はこのファイルに追記してください）