CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
安定版リリースごとに変更点を記録してください。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-17
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムのコアモジュールを追加。
  - パッケージバージョン: 0.1.0
- 環境設定管理 (kabusys.config)
  - .env / .env.local からの自動読み込み（プロジェクトルートの検出は .git または pyproject.toml 基準）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサ実装: export プレフィックス、クォート文字列、インラインコメント、エスケープ処理に対応。
  - 環境変数取得ヘルパ (Settings): J-Quants トークン、kabu API パスワード、Slack 設定、DB パス、実行環境 (development / paper_trading / live)、ログレベル検証、利便性プロパティ（is_live / is_paper / is_dev）。
  - OS 環境変数を保護する override / protected の仕組み。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーの取得機能を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守（RateLimiter 実装）。
  - リトライロジック: 指数バックオフ（最大 3 回）、408/429/5xx を対象にリトライ。
  - 401 応答時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライ。
  - ページネーション対応（pagination_key の追跡）。
  - データ保存関数（save_*）は DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）。
  - fetched_at を UTC で記録し、データ取得時刻のトレースを可能に（Look-ahead Bias 対策）。
  - 型変換ユーティリティ (_to_float / _to_int) を追加し、不正値・空値を安全に扱う。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と DuckDB への保存ワークフローを実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
  - 記事IDは URL を正規化して SHA-256（先頭32文字）で生成し冪等性を保証（utm_* 等のトラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - XML パースに defusedxml を使用して XML Bomb 等の攻撃を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時にスキームとホスト/IP の事前検証を行うハンドラを実装。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストなら拒否。
    - DNS 解決失敗時は安全側（非プライベート）として扱う設計。
  - レスポンスサイズ制御: 最大受信バイト数を 10 MB に制限、gzip 解凍後も検証（Gzip bomb 対策）。
  - テキスト前処理: URL除去、空白正規化、前後トリム。
  - raw_news へのバルク INSERT はチャンク処理、1 トランザクションで実行し、INSERT ... RETURNING により実際に挿入された記事IDを返却。
  - 記事と銘柄コードの紐付け用関数（save_news_symbols / _save_news_symbols_bulk）を実装。重複排除とチャンク挿入を行う。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し known_codes セットでフィルタリング（重複排除）。
- DuckDB スキーマ定義および初期化 (kabusys.data.schema)
  - 3 層データモデル（Raw / Processed / Feature）および Execution レイヤのテーブル定義を追加。
  - raw_prices / raw_financials / raw_news / raw_executions を含む Raw テーブル群。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル群。
  - features, ai_scores 等の Feature テーブル群。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル群。
  - 各種 CHECK 制約、PRIMARY KEY、外部キー、頻出クエリ向けの INDEX を定義。
  - init_schema(db_path) でディレクトリ自動作成と冪等のテーブル初期化を実行。get_connection() で既存 DB に接続。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新戦略を実装:
    - DB 側の最終取得日を参照して新規分のみ取得。
    - backfill_days による数日前からの再取得で API の後出し修正を吸収。
    - 市場カレンダーは先読み（デフォルト 90 日）設定。
  - ETLResult データクラスを実装し、取得数・保存数・品質問題・エラー一覧を保持。
  - テーブル存在チェック、最大日付取得ユーティリティを提供。
  - run_prices_etl の骨組みを実装（差分取得、保存、ロギング）。（未完の戻り値部分はコード内で継続実装を想定）
- パッケージ公開情報
  - src/kabusys/__init__.py にバージョン 0.1.0 と __all__ を追加。

Changed
- 初期リリースにつき該当なし。

Fixed
- 初期リリースにつき該当なし。

Security
- news_collector に SSRF 対策（スキーム検証、プライベートIPブロッキング、リダイレクト検査）を実装。
- defusedxml を用いた XML パースによる XML 関連攻撃の軽減。
- HTTP レスポンスサイズと gzip 解凍後サイズの上限チェックでメモリDoS対策。

Notes / Migration
- 初回リリース。既存データベースを使用する場合は init_schema() を実行してテーブルを作成してください。
- .env の自動ロードはプロジェクトルートの検出に依存します。テスト時などで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN が必要です（Settings.jquants_refresh_token が未設定の場合は例外を投げます）。

Acknowledgements
- 本リリースはコアのデータ取得・保存・ETL・ニュース収集基盤を提供します。戦略ロジック（strategy）、実行エンジン（execution）、監視（monitoring）はパッケージ骨組みとして存在しますが、各機能の詳細実装は今後のリリースで追加予定です。