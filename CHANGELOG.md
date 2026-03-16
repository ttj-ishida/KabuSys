CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョンポリシー: このリポジトリではセマンティックバージョニングを想定しています。

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-16
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基盤機能を実装。
- パッケージ初期化:
  - パッケージルート: kabusys.__init__.py にて __version__ = "0.1.0"、公開サブパッケージを定義。

- 設定/環境変数管理 (kabusys.config):
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env と .env.local を OS 環境変数を保護しつつ読み込む優先度ルールを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パースの堅牢化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォート有無での違い）など。
  - 環境変数の必須チェック _require() と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / システム環境（KABUSYS_ENV, LOG_LEVEL）等のプロパティを用意し、妥当性検証（許容値チェック）およびデフォルト値を提供。
  - settings = Settings() の単一インスタンスを公開。

- J-Quants API クライアント (kabusys.data.jquants_client):
  - API 呼び出しユーティリティを提供（_request）。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制御（_RateLimiter）。
  - リトライ戦略: 指数バックオフ、最大 3 回リトライ、408/429/5xx を考慮。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン処理: refresh token から id token を取得する get_id_token、およびモジュール内キャッシュと 401 時の自動リフレッシュ（1 回のみ）を実装。
  - データ取得関数（ページネーション対応）を実装:
    - fetch_daily_quotes（株価日足/OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 挿入時に ON CONFLICT DO UPDATE を利用して重複を排除・更新。
  - データ型変換ユーティリティ: _to_float, _to_int（厳密な変換ルール: 空値・不正値は None、"1.0" のような float 文字列の int 変換ロジック等）。
  - 取得時刻（fetched_at）を UTC ISO8601（Z）で記録し、Look-ahead bias のトレースを可能に。

- DuckDB スキーマ管理 (kabusys.data.schema):
  - DataPlatform の 3 層（Raw / Processed / Feature）+ Execution レイヤーに基づく包括的な DDL 定義を実装。
  - 以下を含むテーブル群を定義（いずれも CREATE TABLE IF NOT EXISTS、冪等性を確保）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 実行時のインデックス定義を追加（頻出クエリ向け）。
  - init_schema(db_path) による DB 初期化（親ディレクトリ自動作成、:memory: サポート）と get_connection() を提供。

- ETL パイプライン (kabusys.data.pipeline):
  - 日次 ETL のエントリポイント run_daily_etl() を実装（カレンダー取得 → 株価 → 財務 → 品質チェックの順）。
  - 個別ジョブを分離: run_calendar_etl, run_prices_etl, run_financials_etl。差分更新ロジック・バックフィル・カレンダー先読みをサポート。
  - 差分更新のためのヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 営業日調整 util: _adjust_to_trading_day（market_calendar に基づき非営業日を直近営業日に調整、最大 30 日遡る）。
  - ETLResult dataclass により取得数・保存数・品質問題・エラーを集約し、to_dict() でシリアライズ可能。
  - エラーハンドリング方針: 各ステップは独立して例外を捕捉し、1 ステップ失敗でも他のステップは継続（Fail-Fast ではない）。品質チェックは収集方式。

- 監査ログ（トレーサビリティ） (kabusys.data.audit):
  - 監査用スキーマを実装（signal_events, order_requests, executions）。
  - 監査の設計原則に従い、UUID ベースのトレーサビリティ階層、冪等キー（order_request_id）、すべての TIMESTAMP を UTC で保存する方針を反映。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（UTC タイムゾーン設定とインデックスの作成）。
  - ステータス列やチェック制約を含み、エラーや棄却も必ず永続化する設計。

- データ品質チェック (kabusys.data.quality):
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - チェック実装（SQL ベース、DuckDB 接続を受け取り効率的に処理）:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。検出時はサンプル最大 10 行を含む QualityIssue を返す。
    - check_spike: 前日比の変化率によるスパイク検出（LAG ウィンドウを利用）。デフォルト閾値は 0.5（50%）。
  - 各チェックは全件収集方式で実行し、呼び出し側が重大度に応じて判断できる。

- その他
  - ロギング: 各モジュールで logger を使用し、主要イベント（取得件数、保存件数、リトライ、スキップ行数、品質異常など）を記録。
  - エラーメッセージやワーニング出力（.env 読込失敗時など）を実装してデバッグを容易に。

Changed
- 新規初期リリースのため該当なし。

Fixed
- 新規初期リリースのため該当なし。

Removed
- 新規初期リリースのため該当なし。

Security
- 環境変数の取り扱いにおいて OS 環境を保護する protected set を導入し、.env の上書きから保護する仕組みを追加（テストや運用での誤上書きを低減）。

Notes / 今後の改善案（推奨）
- テストカバレッジ: ネットワーク層（HTTPError / URLError）、.env パーサーの境界ケース、ETL の統合テストを追加推奨。
- 並列化: 現在は固定間隔のスロットリングを採用。大規模データ取得での最適化（バースト許容や分散処理）を要検討。
- リトライポリシーの拡張: 特定ステータス毎のカスタムポリシーや最大総待ち時間の制御を検討。
- メトリクス: ETL 実行時間、レートリミット使用率、品質チェック件数等のメトリクス収集を追加すると運用性が向上。

作者・貢献者
- コードベースから推測して作成（詳細な著者情報はリポジトリのコミット履歴を参照してください）。