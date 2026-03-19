CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

 - （なし）

[0.1.0] - 2026-03-19
-------------------

Added
^^^^^

- パッケージ初回リリース。パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として設定。
- 環境設定管理機能を追加（src/kabusys/config.py）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込み。
  - export KEY=val 形式、クォート、インラインコメントなどに対応する堅牢なパース実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 必須環境変数取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境（KABUSYS_ENV）の値チェック（development, paper_trading, live）および LOG_LEVEL 検証。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足データ・財務データ・マーケットカレンダー取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限（120 req/min 固定間隔スロットリング）実装（内部 _RateLimiter）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）、429 の Retry-After 優先処理。
  - 401 受信時は自動でトークンをリフレッシュして1回リトライ（トークン取得は get_id_token）。
  - 取得データを DuckDB に冪等的に保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による upsert 実装。
  - 型変換ユーティリティ（_to_float, _to_int）を備え、入力の堅牢性を向上。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS フィード取得（fetch_rss）、記事前処理（URL 除去・空白正規化）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
  - defusedxml による XML パースで XML Bomb 等の攻撃を防御。
  - SSRF 対策（取得前のホスト検査、リダイレクト時のスキーム/プライベートアドレス検査用ハンドラ）、受信バイト数上限（10MB）チェック、gzip 解凍後のサイズ検査。
  - トラッキングパラメータ除去（utm_* 等）を含む URL 正規化。
  - DuckDB への冪等保存（save_raw_news, save_news_symbols, _save_news_symbols_bulk）をサポートし、INSERT ... RETURNING で実際に挿入された行を返す。トランザクション管理（begin/commit/rollback）実装。
  - 本文中から銘柄コード（4桁）を抽出する extract_stock_codes を提供。run_news_collection により複数ソース一括収集と銘柄紐付けを実行。

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）。
  - Raw 層（raw_prices, raw_financials, raw_news, raw_executions など）の DDL を定義。
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）設計に沿ったテーブル群を準備（Raw 層の主要テーブルを実装、Execution テーブル定義を含む）。

- 研究用（Research）モジュールを追加（src/kabusys/research/*）。
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、DuckDB からの一括取得）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関を標準ライブラリだけで実装。
    - ファクター統計サマリー（factor_summary）とランク付けユーティリティ（rank）。
    - pandas 等の外部ライブラリに依存しない設計。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum: 1M/3M/6M リターン、MA200 乖離率）
    - ボラティリティ/流動性（calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - バリュー（calc_value: PER/ROE を raw_financials と当日株価から計算）
    - DuckDB 上の prices_daily / raw_financials のみを参照する安全設計。
  - research パッケージの __init__ により主要関数をエクスポート（calc_momentum 等）。

- パッケージ構造を整理（src/kabusys/config.py, data/, research/, strategy/, execution/, monitoring プレースホルダ）。

Changed
^^^^^^^

- （初回リリースのため該当なし）

Fixed
^^^^^

- （初回リリースのため該当なし）

Security
^^^^^^^^

- news_collector: defusedxml を使用した XML パース、SSRF 防止のためのホスト/IP チェックとリダイレクト検査、受信サイズ制限、許可スキーム厳格化（http/https のみ）を導入。
- jquants_client: API レート制限と再試行戦略による安定性向上。トークン再取得時の無限再帰防止処理を追加。

Notes / Migration
^^^^^^^^^^^^^^^^^

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings を通して必須取得されます。未設定時は ValueError を送出します。
- デフォルト DB パス:
  - DUCKDB_PATH は data/kabusys.duckdb（展開済 Path）、SQLITE_PATH は data/monitoring.db をデフォルトで使用します。
- 自動 .env 読み込み:
  - プロジェクトルートが検出できない場合は自動読み込みをスキップします。
  - .env.local は .env を上書き（override=True）します。OS 環境変数は保護されます。
  - テスト等で自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Research モジュールは pandas などに依存しない実装のため、大規模データ処理での最適化は今後の課題です。
- news_collector の extract_stock_codes は known_codes（有効コードセット）を引数に取り、該当するコードのみを抽出します。known_codes を渡さないと抽出をスキップできます。

Breaking Changes
^^^^^^^^^^^^^^^^

- 初回リリースのため破壊的変更はありません。

Acknowledgements / その他
^^^^^^^^^^^^^^^^^^^^^^^^^

- 本バージョンはデータ取得（J-Quants）、ニュース収集、DuckDB スキーマ、基礎的なファクター計算およびツール群をワンパッケージで提供する初期実装です。今後、Strategy / Execution / Monitoring の具体的実装、テストカバレッジ拡充、パフォーマンス最適化、外部ライブラリ（pandas 等）を用いた高速化、CLI / scheduled job の追加を予定しています。