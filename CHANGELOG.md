# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
このプロジェクトはセマンティック・バージョニングに従います。

フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]

（現時点の差分はありません）

## [0.1.0] - 2026-03-17

初回リリース — KabuSys 0.1.0

### Added

- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む仕組みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。これにより CWD に依存しない自動読み込みを実現。
  - .env のパース処理を充実：
    - export KEY=val 形式対応、クォート処理、インラインコメント処理など。
  - .env 自動読み込みの優先順位を実装（OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で使用可能）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得：
    - J-Quants / kabu API / Slack / データベースパス等の必須・既定値プロパティ。
    - KABUSYS_ENV 値検証（development / paper_trading / live）。
    - LOG_LEVEL 検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
  - レート制御（_RateLimiter）を実装し、120 req/min の制限を守る固定間隔スロットリングを導入。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）を実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライする機能を追加。
  - id_token キャッシュ（モジュールレベル）を導入してページネーション間で共有。
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar の取得関数を実装（ページネーション対応）。
  - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装：
    - 冪等性を保つため INSERT ... ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC ISO8601 で記録して Look-ahead Bias を軽減。
  - データ変換ユーティリティ（_to_float、_to_int）を実装して堅牢に数値変換を扱う。
  - ロギングを充実させて取得・保存件数や警告を記録。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを取得して raw_news テーブルに保存するモジュールを実装。
  - セキュリティ対策：
    - defusedxml を利用して XML Bomb 等の攻撃を防止。
    - SSRF 対策としてホスト/IP のプライベート判定、リダイレクト先検査を行うカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）を導入。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査を実装（Gzip Bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）および記事 ID 生成（SHA-256 の先頭32文字）を実装し、冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装（preprocess_text）。
  - RSS 解析と記事抽出（fetch_rss）を実装：content:encoded の優先読み取り、pubDate のパース（_parse_rss_datetime）。
  - DuckDB への保存機構：
    - save_raw_news：INSERT ... RETURNING id を用いて新規挿入された記事 ID のみを返す。チャンク処理とトランザクションを導入。
    - save_news_symbols / _save_news_symbols_bulk：news_symbols テーブルへの紐付けを一括保存（重複除去、チャンク挿入、INSERT ... RETURNING で正確な挿入数を取得）。
  - 銘柄コード抽出（extract_stock_codes）：テキスト内の 4 桁コード抽出と既知コードセットによるフィルタリング。
  - run_news_collection：複数 RSS ソースを順次処理し、失敗ソースはスキップして継続する堅牢な収集ジョブを実装。既知コードセットが与えられた場合、収集済み新規記事に対して銘柄紐付けを行う。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層にわたるスキーマ定義 DDL を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 各種チェック制約（NOT NULL, CHECK 等）を定義しデータ整合性を担保。
  - 頻出アクセス向けのインデックス定義を追加。
  - init_schema(db_path) を実装：親ディレクトリの自動作成、DDL とインデックスの順次適用（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass を導入し、ETL 実行結果の構造化（取得数、保存数、品質問題、エラー一覧）を実装。
  - 品質問題の判定補助（has_quality_errors / has_errors）と辞書化 utilities を実装。
  - テーブル存在判定、最大日付取得のユーティリティ関数を実装（_table_exists / _get_max_date）。
  - market_calendar を用いた営業日調整ヘルパー（_adjust_to_trading_day）を実装。
  - 差分更新用ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）を追加。
  - run_prices_etl を実装：
    - 差分更新ロジック（最終取得日 - backfill_days による再取得）、取得 → 保存の流れを実装。
    - jquants_client の fetch/save を用いてデータを取得・保存し、取得件数・保存件数を返す設計。
  - 各所でロギングを強化し、ETL のトレースを容易に。

- テスト支援
  - news_collector 内の _urlopen をモック可能にしてネットワーク操作を置き換えやすくしている（テスト容易性の配慮）。
  - jquants_client の id_token 注入可能設計によりユニットテストが容易。

### Fixed

- 初回リリースにつき該当なし。

### Security

- RSS パーサに defusedxml を使用して XML 関連の脆弱性対策を実施。
- SSRF 対策を複数レイヤで実装（事前ホスト検査、リダイレクト検査、スキーム制限、プライベート IP 判定）。
- ネットワーク応答サイズと gzip 解凍後サイズの検査でメモリ DoS 対策を導入。
- .env 読み込み時に OS 環境変数を protected として上書き防止できる仕組みを提供。

### Changed

- 初回リリースにつき過去からの変更はなし。

### Deprecated

- なし

### Removed

- なし

### Known issues / Notes

- run_prices_etl や ETL 周りは差分更新・バックフィル・品質チェックの骨格が実装されていますが、品質チェックモジュール（kabusys.data.quality）の詳細実装や ETL を定期実行するオーケストレーションは今後の実装対象です。
- 0.1.0 は初期実装のため、運用での大量データや異常系を想定した追加の堅牢化・監視設定が必要になる場合があります（ログ設定、リトライポリシー微調整、メトリクスのエクスポート等）。

---

署名: KabuSys 開発チーム