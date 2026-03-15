# Changelog

すべての変更は Keep a Changelog のガイドライン（https://keepachangelog.com/ja/1.0.0/）に従って記載します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース。パッケージの基本構成、環境設定管理、DuckDB スキーマ定義と初期化の実装を追加。

### Added
- パッケージ基盤
  - Python パッケージ `kabusys` を追加。
  - バージョンを `__version__ = "0.1.0"` に設定。
  - サブパッケージの公開インターフェースを定義（data, strategy, execution, monitoring）。各サブパッケージの __init__.py を配置（将来の拡張用に空実装）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトのルート検出: __file__ を起点に `.git` または `pyproject.toml` を探索してプロジェクトルートを特定（CWD 非依存）。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - .env ファイル読み込み時、OS 環境変数を保護するための `protected` キー集合をサポートし、必要に応じて上書きを制御。
  - .env パース機能を実装
    - 空行・コメント行（`#` で始まる）を無視。
    - `export KEY=val` 形式に対応。
    - クォートされた値（シングルクォート／ダブルクォート）に対してバックスラッシュエスケープを処理し、対応する閉じクォートまでを値として扱う。
    - クォートなしの値では、`#` の直前がスペースまたはタブであれば以降をコメントとして扱う（インラインコメントの取り扱い）。
    - 無効な行・キーに対してはスキップ。
  - Settings クラスを提供（環境変数からの値取得とバリデーション）
    - J-Quants / kabuステーション / Slack / データベースパスなどの設定プロパティを実装。
    - 必須設定が未設定の場合は ValueError を投げる `_require()` を用意。
    - `duckdb_path` / `sqlite_path` は Path 型で返す（デフォルトパスを持つ）。
    - 環境種別 `KABUSYS_ENV` とログレベル `LOG_LEVEL` に対する許容値チェックを実装（許容値はそれぞれ `development|paper_trading|live`, `DEBUG|INFO|WARNING|ERROR|CRITICAL`）。
    - 利便性プロパティ `is_live`, `is_paper`, `is_dev` を実装。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataLayer 構成に従うテーブル群を追加（Raw / Processed / Feature / Execution の 4 層）。
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型・チェック制約・PRIMARY KEY・外部キーを適切に設定
    - 例: prices_daily の low カラムに low <= high の CHECK 制約、orders と signal_queue の外部キー関係、trades の order_id による ON DELETE CASCADE など
  - インデックス定義を追加（頻出クエリパターンを想定したインデックス）
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status など
  - スキーマ初期化 API
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスに対して親ディレクトリを自動作成し、全テーブル・インデックスを作成（冪等）。
      - ":memory:" をサポート（インメモリ DB）。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマの初期化は行わない）。
  - 実装上の注意
    - DuckDB に対して複数 DDL を順次実行し、外部キー依存を考慮したテーブル作成順序を管理。

### Notes
- 現在はコアのスケルトン（設定管理・スキーマ）を実装した段階で、戦略ロジックや発注実行の具体実装は未実装（サブパッケージの雛形のみ配置）。
- .env パーサーや自動ロードはテストや CI 環境で挙動を制御できるよう配慮（KABUSYS_DISABLE_AUTO_ENV_LOAD、protected 機構）。
- DuckDB スキーマは将来的に拡張可能な設計（特徴量テーブルや AI スコア、注文/約定の履歴管理を考慮）。

--- 

今後のリリース候補例（想定）
- 0.2.0: データ取得モジュール（価格取得、財務データ、ニュースのフェッチ）を追加、定期実行ジョブの追加。
- 0.3.0: 戦略実装（シグナル生成）、注文送信・監視モジュール（kabu ステーション連携）を追加。
- 1.0.0: ライブ運用対応（安全性・リトライ・ロギング・メトリクス）とドキュメント整備。