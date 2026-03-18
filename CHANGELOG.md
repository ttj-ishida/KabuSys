CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is [Semantic Versioning](https://semver.org/) compliant.

Unreleased
----------
### 修正
- run_prices_etl の戻り値処理が未完（実装不備）
  - 現状の実装断片では run_prices_etl の最後の return が不完全で、(取得件数, 保存件数) のタプルを返す意図のところが途中で切れているため、構文エラーまたは呼び出し側でのアンパック失敗が発生する可能性があります。早急に完全な戻り値（fetched と saved の両方）を返すよう修正が必要です。

### 既知の制限 / TODO
- src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py はプレースホルダ（空ファイル）です。実際の発注・戦略ロジックは未実装です。
- 単体テスト・統合テストの整備が必要（ネットワーク、DuckDB IO、外部API依存の箇所が多いため、モック注入やフィクスチャの追加推奨）。

[0.1.0] - 2026-03-18
--------------------
初期リリース (package version: 0.1.0)。コードベースから推測される主な機能・実装を以下にまとめます。

### 追加
- 基本パッケージ構造
  - kabusys パッケージの基本 __init__ を追加（__version__ = 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring（strategy と execution はプレースホルダ）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む Settings クラスを提供。
  - 自動 .env ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサは export 付き行やクォート（シングル/ダブル）に対応、インラインコメント処理、既存 OS 環境変数保護（protected set）機能を実装。
  - 必須変数取得時は _require() で未設定時に ValueError を投げる。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API のベース実装（_BASE_URL = https://api.jquants.com/v1）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライロジック: 指数バックオフ、最大 3 回、対象ステータス(408,429,5xx)。
  - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグあり）。
  - トークンキャッシュ（モジュールレベル）を提供（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes (日足 OHLCV、ページネーション対応)
    - fetch_financial_statements (四半期 BS/PL、ページネーション対応)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE。
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE。
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE。
  - データ整形ユーティリティ: _to_float, _to_int（厳密な変換ルール）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集機能（デフォルト: Yahoo Finance ビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 防止: リダイレクト時にスキームと最終ホストを検証する _SSRFBlockRedirectHandler。
    - ホストがプライベート/ループバック/リンクローカルの場合は拒否する _is_private_host。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス最大バイト数制限 (MAX_RESPONSE_BYTES = 10 MB) と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ削除:
    - _normalize_url は utm_*, fbclid, gclid 等のパラメータを削除し、クエリをソート、フラグメント削除を行う。
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字を使用（冪等性の確保）。
  - 記事前処理: URL 除去、空白正規化（preprocess_text）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING を使い、新規挿入記事 ID の一覧を返す。チャンク分割と 1 トランザクションでの挿入。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンクで INSERT ... RETURNING により正確にカウント。
  - 銘柄コード抽出: テキスト中の4桁数字候補を known_codes セットでフィルタして抽出する extract_stock_codes。
  - run_news_collection: 複数 RSS ソースからの収集・保存・銘柄紐付けの統合ジョブ（ソース単位でエラーハンドリング）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 3 層（＋実行層）に基づくテーブル DDL を実装。
  - 主なテーブル（抜粋）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, orders, trades, positions, portfolio_performance など
  - 制約（PRIMARY KEY, CHECK）と外部キーを含むスキーマ。
  - インデックスセットを定義（頻出クエリ向け: code×date, status 検索等）。
  - init_schema(db_path) によりディレクトリ自動生成 → DuckDB 接続を返し、全 DDL とインデックスを適用（冪等）。
  - get_connection(db_path) により既存 DB へ接続（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新ベースの ETL 設計:
    - DB の最終取得日からの差分取得、自動 backfill（デフォルト backfill_days=3）で API の後出し修正を吸収。
    - 市場カレンダーは先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）。
    - 初回ロード用に J-Quants データ最小日付を _MIN_DATA_DATE = 2017-01-01 として定義。
  - ETLResult dataclass: ETL 実行結果、品質問題、エラー一覧を保持。to_dict() で出力整形。
  - テーブル存在チェック、最大日付取得などのユーティリティ関数 (_table_exists, _get_max_date)。
  - 市場日調整ヘルパー: _adjust_to_trading_day（非営業日→直近の営業日へ調整）。
  - 個別 ETL ジョブ（実装済の一部）:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl: 差分取得 → jq.fetch_daily_quotes → jq.save_daily_quotes（※注: 現状戻り値実装不備あり）

### 変更
- （初期リリースのため過去履歴無し）

### 修正
- （初期リリースのため過去修正無し）

### セキュリティ
- ニュース収集での SSRF 防止、defusedxml の採用、HTTP レスポンスサイズチェックなどのセキュリティ対策を導入。

その他メモ
----------
- DuckDB（duckdb パッケージ）へ依存するため、本プロジェクトを動かす際は該当依存をインストールしてください。
- ネットワーク呼び出し (urllib) を直接使っている箇所が多いため、ユニットテスト時はモック（例えば news_collector._urlopen や jquants_client の HTTP 呼び出し）を注入すると安定的にテスト可能です。
- ETL の品質チェック（quality モジュール参照）は pipeline 設計に組み込む想定ですが、quality モジュールの実体はこのスニペットに含まれていません（外部実装依存）。

もし希望であれば、次の対応案を提案します:
- run_prices_etl の戻り値修正プルリクエスト案（取得数・保存数の正しいタプル返却）。
- strategy / execution の基本インターフェースの雛形（タイプヒント付き）を追加。
- CI 用の簡易テスト（DuckDB のインメモリ DB と HTTP 呼び出しモック）を追加するサンプル。