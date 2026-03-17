CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog に準拠しています — https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-17
--------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - エクスポート: data, strategy, execution, monitoring を公開
- 設定管理:
  - 環境変数読み込み機能を実装 (src/kabusys/config.py)。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - export KEY=val 形式、クォート内のエスケープ、行末コメントの取り扱い等に対応する堅牢な .env パーサーを実装。
    - 必須設定取得用 _require 関数と Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル判定など）。
    - 設定値検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）。
- データ取得クライアント:
  - J-Quants API クライアントを追加 (src/kabusys/data/jquants_client.py)。
    - レートリミッタ実装（_RateLimiter、デフォルト120 req/min）。
    - 冪等的／堅牢な HTTP リクエスト処理:
      - 指数バックオフ付きリトライ（最大3回）。
      - 408/429/5xx をリトライ対象、429 時は Retry-After を優先。
      - 401 受信時は自動でリフレッシュを試行して 1 回リトライ。
      - ページネーション対応（pagination_key を追跡）。
    - API → DuckDB の保存ユーティリティ:
      - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
      - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT を使った冪等保存、fetched_at を UTC で記録。
    - 型変換ヘルパー (_to_float, _to_int) を実装し不正値を安全に扱う。
    - テスト可能性: id_token を引数注入可能、モジュールレベルで ID トークンキャッシュを共有。
- ニュース収集:
  - RSS ニュース収集モジュールを追加 (src/kabusys/data/news_collector.py)。
    - RSS フェッチ(fetch_rss) と前処理（URL除去、空白正規化）。
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事 ID を正規化 URL の SHA-256 の先頭32文字で生成（_make_article_id）し冪等性を確保。
    - defusedxml を用いた安全な XML パースと XML Bomb 対策。
    - SSRF 対策:
      - スキーム検証（http/https のみ許可）。
      - リダイレクト時にホストがプライベート/ループバックか検査するハンドラ (_SSRFBlockRedirectHandler)。
      - 事前にホストのプライベート性を確認する仕組み（_is_private_host）。
    - レスポンスバイト数制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後サイズチェック。
    - DuckDB 保存処理:
      - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、挿入された新規記事IDのリストを返す。トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（RETURNING により実際に挿入された件数を取得）。
    - 銘柄コード抽出機能 extract_stock_codes（4桁数字、known_codes フィルタ付き、重複排除）。
    - RSS ソースのデフォルトには Yahoo Finance を含む。
- データスキーマ:
  - DuckDB スキーマ定義と初期化 API を追加 (src/kabusys/data/schema.py)。
    - Raw / Processed / Feature / Execution の多層テーブル群を定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, など多数）。
    - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを用意。
    - init_schema(db_path) でディレクトリ作成→DDL 実行→接続を返す。get_connection で既存 DB に接続可能。
- ETL パイプライン:
  - ETL パイプライン基盤を追加 (src/kabusys/data/pipeline.py)。
    - 差分更新のためのヘルパー（テーブル存在確認、最大日付取得）。
    - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
    - run_prices_etl: 差分更新（バックフィル日数の扱い）と jquants_client 経由の取得／保存の流れを実装（ETLResult を返す設計）。
    - ETLResult dataclass: 実行結果、品質問題、エラー列挙、ユーティリティ to_dict() を含む。
    - 設計方針: デフォルトで backfill_days=3、品質チェックとの統合を想定（quality モジュールと協調）。

Security
- 外部データ取得でのセキュリティ強化:
  - RSS/HTTP の SSRF 対策（スキーム検証、プライベートホスト検出、リダイレクト検査）。
  - XML の安全パーサ（defusedxml）採用。
  - レスポンスサイズ上限と gzip 解凍後の検査で DoS のリスクを低減。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set により上書き制御）。

Design decisions / Notes
- 冪等性を重視:
  - raw データの保存は ON CONFLICT DO UPDATE/DO NOTHING を利用して重複・再取得に安全に対応。
  - ニュース記事 ID は URL 正規化→ハッシュで決定し同一記事の重複挿入を抑止。
- API 呼び出しはレート制限とリトライ戦略を組み合わせ、トークン自動リフレッシュをサポート。
- テストしやすさを考慮:
  - RSS の低レベル接続点 (_urlopen) をモック可能にしている。
  - API トークンを引数で注入できる設計。
- 一部モジュール（strategy、execution、monitoring）はパッケージインターフェースとして存在するが、今回のリリースでは実装が最小（__init__ が空）になっている。

Fixed
- 初回リリースのため該当なし（実装中心の追加）。

BREAKING CHANGES
- なし（初回リリース）。

今後の予定（非網羅）
- ETL の完全な品質チェック統合（quality モジュールの実装/接続）。
- strategy / execution 層の実装（シグナル生成→注文発行→約定処理までのワークフロー）。
- 監視（monitoring）と Slack 通知等の運用機能拡充。

もし CHANGELOG に含めてほしい追加情報（例えば実際のコミットID、より詳細な日付、リリース手順、外部依存バージョンなど）があれば教えてください。