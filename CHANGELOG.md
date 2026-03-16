CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
各バージョンには後から追記される可能性があります。

Unreleased
----------
- なし

0.1.0 — 2026-03-16
------------------
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点と設計上の要点は以下の通りです。

Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py にてバージョンを 0.1.0 に設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用）。
    - export KEY=val 形式、シングル/ダブルクォートのエスケープ、行内コメント処理等を考慮した .env パーサ実装。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境名 / ログレベル等のプロパティを取得（必須項目は未設定時に ValueError を送出）。
    - 環境値の妥当性検査（KABUSYS_ENV, LOG_LEVEL）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - API 呼び出しでのレート制限（120 req/min）を固定間隔スロットリングで実装。
    - リトライ（指数バックオフ）実装：最大 3 回、対象ステータス 408/429/5xx およびネットワークエラー。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュ化（ページネーション間で共有）。
    - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等的に保存する save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias 対策を考慮。
    - 型変換ユーティリティ (_to_float, _to_int)。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の 3 層（＋監査層）に準拠したテーブル定義群を実装（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions 等）。
    - 制約（PRIMARY KEY, CHECK）や実行時に役立つインデックスを定義。
    - init_schema(db_path) でディレクトリ作成からテーブル・インデックス作成までを冪等に初期化、get_connection で既存 DB に接続可能。

- ETL パイプライン
  - src/kabusys/data/pipeline.py
    - 日次 ETL のエントリ run_daily_etl を実装（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）。
    - 差分更新ロジック（DB の最終取得日からの再取得）、デフォルトの backfill_days（3 日）による後出し修正吸収。
    - カレンダーは lookahead（デフォルト 90 日）で先読みして営業日調整に使用。
    - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他のステップは継続する設計。
    - ETLResult データクラスで結果・品質問題・エラーを集約（監査ログや通知に利用しやすい to_dict を提供）。

- データ品質チェック
  - src/kabusys/data/quality.py
    - QualityIssue データクラス。
    - check_missing_data: raw_prices の必須カラム（open/high/low/close）欠損検出（サンプル行付き報告）。
    - check_spike: LAG ウィンドウで前日比スパイク検出（閾値デフォルト 50%）。
    - 各チェックは Fail-Fast とせず、問題をすべて収集して呼び出し元に返す設計。DuckDB 上で効率的に SQL 実行。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py
    - signal_events, order_requests（order_request_id を冪等キーとして利用）, executions の DDL を実装。
    - 監査用インデックス群、UTC タイムゾーン強制（SET TimeZone='UTC'）。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供し、監査テーブルを既存接続へ追加可能。

- その他ユーティリティ
  - rate limiter クラス、API リクエストユーティリティ、データ型変換ユーティリティなどを内部実装。

Design / Notes
- 冪等性: データ保存は ON CONFLICT DO UPDATE を利用して冪等に実装。
- トレーサビリティ: すべての監査テーブルに created_at を持ち、order_request_id による冪等性と UUID 連鎖でシグナル→発注→約定を追跡可能に設計。
- 時刻の取り扱い: すべての fetched_at / 監査タイムスタンプは UTC に統一。
- API 耐障害性: レート制御・リトライ・トークン自動リフレッシュを組み合わせ、運用環境での安定性を重視。
- ドキュメント参照: 各モジュールに DataPlatform.md / DataSchema.md 等の設計参照を記載。

Changed
- 初回リリースのため変更履歴なし。

Fixed
- 初回リリースのため修正履歴なし。

Security
- 初回リリース。セキュリティ関連の注意点:
  - .env の自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 秘密情報（トークン・パスワード等）は環境変数経由で管理する想定。

Acknowledgements
- 初期実装のための主要ファイル一覧:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/schema.py
  - src/kabusys/data/pipeline.py
  - src/kabusys/data/audit.py
  - src/kabusys/data/quality.py

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装拡充（現状はパッケージプレースホルダ）。
- より詳細な品質チェック（重複チェック、将来日付検出、ニュース関連チェックなど）の追加。
- 単体テスト・統合テストの追加および CI 統合。

--- 
(END)