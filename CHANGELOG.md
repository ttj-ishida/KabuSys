CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" とセマンティックバージョニングを念頭に置いています。

[Unreleased]
------------

- （現時点なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
- パッケージ公開情報:
  - バージョン: 0.1.0
  - パッケージトップ: src/kabusys/__init__.py（__version__ = "0.1.0"）
- 環境設定管理（src/kabusys/config.py）:
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .git または pyproject.toml を基準にプロジェクトルートを自動検出（配布後も CWD に依存しない）。
  - .env パーサー実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行末コメントの取り扱いを実装。
  - Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、環境/ログレベル検証など）。
  - 必須環境変数未設定時は ValueError を送出する保護的設計。
- J-Quants クライアント（src/kabusys/data/jquants_client.py）:
  - API 呼び出しユーティリティを実装（_request）。
  - レート制御（固定間隔スロットリング、デフォルト 120 req/min）を実装。
  - リトライ戦略（指数バックオフ、最大 3 回。ステータス 408/429/5xx を対象）。
  - 401 受信時に refresh（id_token 自動リフレッシュ）して 1 回リトライする処理を実装。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得データに対して fetched_at（UTC）を付与して look-ahead bias のトレースを可能に。
  - 入力データ変換ユーティリティ: _to_float, _to_int
- ニュース収集モジュール（src/kabusys/data/news_collector.py）:
  - RSS フィードから記事を収集し raw_news に保存するワークフローを実装。
  - セキュリティ対策と堅牢化:
    - defusedxml による XML パーシング（XML Bomb 等の対策）。
    - リダイレクト先のスキーム/ホストを検査して SSRF を防止するカスタム RedirectHandler。
    - URL スキーム検証（http/https のみ許可）。
    - Content-Length / 実読込サイズの上限チェック（デフォルト 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 受信ヘッダの Accept-Encoding:gzip サポート。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を採用して冪等性を確保（utm_* 等の追跡パラメータを除去）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news はチャンク式 INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規挿入された記事 ID のリストを返す。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄の紐付けを一括保存（重複排除・トランザクション管理）。
  - 銘柄抽出: テキスト中の 4 桁数字を抽出し、known_codes に含まれるもののみを返す（重複除去）。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリ RSS を設定。
- スキーマ定義（src/kabusys/data/schema.py）:
  - DuckDB 用のスキーマをまとめて定義（Raw / Processed / Feature / Execution の多層構造）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤーテーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
  - features, ai_scores 等の Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) でディレクトリ自動作成（必要な場合）と DDL 実行による初期化を提供（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン（src/kabusys/data/pipeline.py）:
  - ETLResult dataclass を実装（対象日、取得/保存数、品質問題、エラー情報などを保持）。
  - DuckDB ヘルパー: テーブル存在チェック、最大日付取得、営業日調整ロジック（market_calendar 利用）を実装。
  - 差分更新ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - run_prices_etl を実装（差分更新ロジック: 最終取得日から backfill_days を遡って再取得、fetch + save の実行）。デフォルト backfill_days = 3。
  - 設計方針:
    - 差分更新をデフォルト単位「営業日1日分」ベースで自動算出。
    - 品質チェックは fail-fast を避け、問題は収集して呼び出し元に判断させる設計（quality モジュールとの連携想定）。
    - id_token の注入でテスト容易性を確保。
- モジュール構成:
  - data, strategy, execution, monitoring のパッケージがルート __all__ に含まれる（strategy と execution は初期プレースホルダを配置）。

Security
- news_collector モジュールに複数の SSRF / XML / DoS 緩和策を導入（上記参照）。
- J-Quants API クライアントでは認証トークンの自動リフレッシュと安全なリトライ方針を採用。

Known issues / Notes
- run_prices_etl の末尾の return が不完全（コード断片または編集漏れの可能性）。現状では (取得件数, 保存件数) を返す想定だが、ソース内の最後の return 文が不完全になっているため修正が必要。
- Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出するため、実行環境での .env 設定が必須。
- news_collector の RSS フェッチは外部ネットワークに依存するため、テスト時は _urlopen をモックする設計（コード内にその旨のコメントあり）。
- schema.init_schema は DuckDB を使用するため、実行時に duckdb パッケージが必要。
- pipeline 実装は ETL の基本骨組みを提供しているが、quality モジュールとの連携や他の ETL ジョブ（財務・カレンダー・ニュース等）の run_* 実装は今後追加される想定。

Removed
- （なし）

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

References
- 各実装ファイル:
  - src/kabusys/config.py
  - src/kabusys/data/jquants_client.py
  - src/kabusys/data/news_collector.py
  - src/kabusys/data/schema.py
  - src/kabusys/data/pipeline.py

今後の作業提案
- run_prices_etl の戻り値バグ（不完全な return 文）を修正してテスト追加。
- その他 ETL ジョブ（財務データ、カレンダー、ニュース集約など）の run_* 実装と品質チェックの統合。
- strategy / execution / monitoring モジュールの具体実装と統合テストの追加。
- CI 環境向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を使った環境切替テストを整備。