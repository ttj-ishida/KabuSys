CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

初回リリース。日本株自動売買基盤「KabuSys」のコアモジュール群を追加しました。
主に環境設定、データ取得・保存、ニュース収集、DuckDBスキーマ定義、ETLパイプラインの実装を含みます。

Added
- パッケージのバージョン管理を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env ファイルの堅牢なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理対応）。
  - OS 環境変数を保護するための上書き制御（.env.local は上書きモード）。
  - 必須環境変数取得ヘルパー _require と Settings クラス（J-Quants、kabu、Slack、DBパス、実行環境判定等）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得機能を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限管理（固定間隔スロットリング: 120 req/min）を実装する内部 RateLimiter。
  - リトライ／バックオフ戦略（指数バックオフ、最大 3 回）。HTTP 408/429/5xx の再試行処理、429 時は Retry-After ヘッダ優先。
  - 401 レスポンス時にリフレッシュトークンで id_token を自動更新して一度リトライするロジック（無限再帰を防止）。
  - id_token キャッシュ共有（モジュールレベル）と注入可能な id_token 引数（テスト容易性）。
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE を利用した save_daily_quotes, save_financial_statements, save_market_calendar）。
  - 取得日時（fetched_at）を UTC ISO フォーマットで記録して Look-ahead Bias を抑制。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に None に変換。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集機能（fetch_rss）および DuckDB への保存（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256 ベースの記事ID生成（先頭32文字）で冪等性を確保。
  - XML パースに defusedxml を使用して XML Bomb 等の攻撃を緩和。
  - SSRF 対策:
    - リクエスト前にホストのプライベート/ループバック判定を行う _is_private_host。
    - リダイレクト時にスキームとホスト検証する _SSRFBlockRedirectHandler を導入。
    - http/https 以外のスキームを拒否。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
  - コンテンツ前処理（URL 除去、空白正規化）、pubDate の堅牢なパース（_parse_rss_datetime）。
  - 銘柄コード抽出ロジック（4桁数字、known_codes フィルタ）と一括登録のためのチャンク/トランザクション処理。
- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加。
  - テーブル群: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 代表的なインデックス定義（頻出クエリに備えたインデックス）を追加。
  - init_schema(db_path) でディレクトリ作成・DDL 実行を行い初期化するヘルパーを提供。get_connection() で既存DB接続を取得可能。
- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを導入して ETL 実行結果・品質問題・エラーを集約。
  - 差分更新ヘルパー（最終取得日の取得、非営業日の調整 _adjust_to_trading_day、テーブル存在チェックなど）。
  - run_prices_etl 等の差分ETL の枠組み（差分計算、backfill_days による再取得、J-Quants クライアント経由の取得→保存の流れ）を実装（部分実装）。
  - デフォルト振る舞い: 初回ロードは _MIN_DATA_DATE (2017-01-01) から取得。市場カレンダーは先読み可能（_CALENDAR_LOOKAHEAD_DAYS）。
- パッケージ構造の雛形を追加（execution, strategy, data パッケージの __init__ 等）。

Security
- 環境変数の管理で OS 環境を保護（.env の上書き制御）し、重要なシークレットが意図せず上書きされることを防止。
- news_collector で SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限、gzip 解凍後のサイズチェックを実装。
- jquants_client の id_token 自動リフレッシュ時に無限再帰を避ける仕組みを追加。

Performance / Reliability
- J-Quants API 呼び出しに固定間隔レートリミッタを導入し、レート制限超過を防止。
- 再試行論理と指数バックオフにより一時的なネットワーク障害に耐性を持たせる。
- DuckDB へのバルク挿入はチャンク化してトランザクションにまとめ、INSERT ... RETURNING を使って正確な挿入数を取得。
- News の銘柄紐付けは重複除去し一括で挿入することでオーバーヘッドを削減。

Notes / Usage
- DB 初期化:
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)
- 環境変数（必須例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらは Settings クラスのプロパティ経由でアクセス可能（設定されていない場合はエラーを送出）。
- .env ロード優先順:
  - OS 環境 > .env.local > .env（.env.local は .env を上書き）
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Deprecated
- なし

Removed
- なし

Fixed
- 初回リリースのため該当なし

Breaking Changes
- 初回リリースのため該当なし

補足
- 本 CHANGELOG はコードベース（src/ 以下）から機能・設計意図を推測して記述しています。実際の API 利用法や運用手順は README や設計ドキュメント（DataPlatform.md, DataSchema.md 等）に従ってください。