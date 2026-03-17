# Changelog

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従っています。
セマンティックバージョニングを使用します。

## [Unreleased]

（現在未リリースの変更はここに記載）

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージとバージョン管理（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パッケージ公開 API の __all__ 指定（data, strategy, execution, monitoring）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env および環境変数から設定を自動読み込みするロジックを実装。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に検索。
  - .env / .env.local の読み込み順序（OS 環境 > .env.local > .env）。.env.local は上書き。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - キー必須チェック用の Settings クラス（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス等のプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の正当性検証（有効値制限）。
  - duckdb/sqlite のデフォルトパス設定。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得の実装。
  - API レート制限対応（120 req/min）として固定間隔スロットリングを実装（内部 RateLimiter）。
  - リトライ戦略（指数バックオフ、最大 3 回、対象: 408/429/5xx）。
  - 401 応答を検知してリフレッシュトークンから id_token を自動再取得して 1 回リトライするロジック。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - 取得時間（fetched_at）を UTC で記録し、Look-ahead バイアス対策。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を実装する save_* 関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型安全な変換ユーティリティ（_to_float, _to_int）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得・前処理・DuckDB へ保存する一連処理を実装。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等を防止）。
    - SSRF 対策（許容スキーム限定、プライベート IP/ホスト拒否、リダイレクト時の検査）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の上限検査。
    - URL 正規化によりトラッキングパラメータを除去（utm_ 等）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - 保存機能:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id（挿入された実際の記事IDを返す）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（RETURNING により実際に挿入された数を返す）。
  - テキスト前処理（URL除去・空白正規化）および記事内からの銘柄コード（4桁）抽出ユーティリティ。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 4 層に対応した DDL 定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等 Execution 層。
  - よく使うクエリ向けのインデックスを定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ作成→全テーブル／インデックス作成（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新の概念、および ETLResult データクラスを実装（品質問題やエラーの収集を含む）。
  - DB 側の最終取得日取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダーを用いた営業日調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl の差分取得ロジック（backfill_days による遡り取得、初回は _MIN_DATA_DATE から）。
  - 全体設計において、品質チェックモジュール（quality）との連携を想定。

### 変更 (Changed)
- N/A（初回リリース）

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- RSS 処理で defusedxml を使用し XML 攻撃対策を実施。
- HTTP リダイレクトや最終 URL の検査で SSRF を防止（スキーム検証、プライベートアドレス拒否）。
- レスポンスサイズチェック・gzip 解凍後チェックを実装し、メモリ DoS 対策を実施。
- .env 読み込みは既存 OS 環境変数を保護する保護リスト（protected）を使用。

### 既知の制限・注意事項 (Notes)
- init_schema() は DuckDB のテーブル作成のみを行い、データ移行や既存データの修正を自動化するものではありません。
- J-Quants のレート制限は固定間隔スロットリングで制御しています。大量データ取得時のスループット制御に注意してください。
- news_collector の URL 正規化・トラッキング除去は既知のプレフィックスに基づくため、カバレッジに限界があります。
- pipeline.run_prices_etl などは差分 ETL の骨組みを提供します。品質チェック（quality モジュール）は呼び出し元で適切に評価してください。
- 環境変数は必須項目があり、未設定時は ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

### マイグレーション / 利用開始ガイド (Upgrade / Getting started)
- 必須環境変数を設定してください（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- ニュース収集:
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, known_codes=set_of_known_codes)
- データ取得（株価/財務/カレンダー）:
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存は save_* 関数を使用（DuckDB 接続を渡す）。

---

（今後のリリースでは strategy / execution / monitoring の実装・統合、品質チェックモジュールの詳細化、より細かなエラーレポーティングやメトリクス導入を予定しています）