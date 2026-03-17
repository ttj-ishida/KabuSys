# Changelog

すべての変更は Keep a Changelog の慣習に従って記載します。  
このファイルはリポジトリの初期リリース（v0.1.0）の機能と設計上の要点をコードベースから推測してまとめたものです。

全般的な表記:
- 日付は本ドキュメント作成日（2026-03-17）を使用しています。
- 関数・モジュール名は実装上の重要ポイントを参照しています。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期構成
  - パッケージ名: `kabusys`（src/kabusys）
  - バージョン: `0.1.0` を `src/kabusys/__init__.py` に定義
  - サブパッケージ公開: `data`, `strategy`, `execution`, `monitoring` を __all__ で公開

- 環境設定モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート判定は `.git` または `pyproject.toml` を探索して行う（CWD 非依存）
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env 行パーサ（エスケープ付きクォート、export プレフィックス、インラインコメント等に対応）
  - `.env` 読み込み時のオーバーライド/保護（protected keys）ロジック
  - 必須環境変数取得ヘルパ `_require`（未設定時は ValueError 発生）
  - Settings クラスによるプロパティアクセス
    - J-Quants / kabuステーション / Slack / DB パス等の設定
    - `env` と `log_level` の値検証（許可値のチェック）
    - `is_live`, `is_paper`, `is_dev` の利便性プロパティ

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ `_request`
    - レート制限（120 req/min）を守る固定間隔スロットリング（_RateLimiter）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx に対してリトライ）
    - 401 Unauthorized を検出した場合、自動で ID トークンをリフレッシュして 1 回だけ再試行
    - JSON デコードエラーの詳細メッセージ
  - トークン管理
    - `get_id_token()`：リフレッシュトークンから idToken を取得（POST /token/auth_refresh）
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）
  - データ取得関数（ページネーション対応）
    - `fetch_daily_quotes(...)`：株価日足（OHLCV）
    - `fetch_financial_statements(...)`：四半期財務データ
    - `fetch_market_calendar(...)`：JPX マーケットカレンダー
    - 取得時に fetched_at を UTC で記録する方針を実装（save 側）
  - DuckDB への冪等保存関数
    - `save_daily_quotes(...)`：raw_prices テーブルへ ON CONFLICT DO UPDATE
    - `save_financial_statements(...)`：raw_financials テーブルへ ON CONFLICT DO UPDATE
    - `save_market_calendar(...)`：market_calendar テーブルへ ON CONFLICT DO UPDATE
    - PK 欠損行のスキップやスキップ件数のログ
  - 型変換ユーティリティ `_to_float`, `_to_int`（意図しない切り捨てを防ぐ）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS からニュース収集し raw_news / news_symbols へ保存する一連の処理を実装
  - セキュリティと堅牢性:
    - defusedxml による XML パース（XML Bomb 等への対策）
    - SSRF 対策: リダイレクト時にスキーム検証とプライベートアドレス検査を行うカスタム RedirectHandler を実装
    - URL スキームは http/https のみ許可
    - ホストのプライベートアドレス判定（直接 IP と DNS 解決の両方をチェック）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の再チェック（Gzip bomb 対策）
    - 受信ヘッダの Content-Length による事前チェック
  - URL 正規化と記事ID生成:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去してクエリソートした正規化 URL を作成
    - 記事ID は正規化 URL の SHA-256 の先頭 32 文字を使用（冪等性保証）
  - テキスト前処理（URL 除去、空白正規化）
  - fetch_rss(...)：
    - RSS を安全に取得・パースし、NewsArticle のリストを返す
    - content:encoded 優先で description をフォールバック
  - DB 保存:
    - `save_raw_news(...)`：チャンク分割、1 トランザクション、INSERT ... RETURNING id を利用して新規挿入 ID を返す
    - `save_news_symbols(...)` / `_save_news_symbols_bulk(...)`：news_symbols テーブルへ一括保存（ON CONFLICT DO NOTHING / RETURNING を利用）
  - 銘柄コード抽出:
    - テキスト内の 4 桁数字を抽出し、known_codes と照合して重複除去して返す
  - 統合収集ジョブ:
    - `run_news_collection(...)`：複数ソースを独立して処理し、ソースごとの新規挿入件数を返す
    - 新規挿入記事に対して銘柄紐付けを一括処理

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定したテーブル定義を追加
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）および頻出クエリに対するインデックスを定義
  - `init_schema(db_path)`：ディレクトリ自動作成 + 全テーブルとインデックスの作成（冪等）
  - `get_connection(db_path)`：既存 DB への接続取得（スキーマ初期化は行わない）

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新 / バックフィル（backfill）を考慮した ETL 設計
    - 最終取得日を基に差分のみ取得、デフォルトでは backfill_days = 3
    - 市場カレンダーは先読み（lookahead）で将来日を取得
  - ETL 結果を表す `ETLResult` データクラス（品質チェックの結果やエラーを集約）
  - テーブル存在チェック `_table_exists`、最大日付取得 `_get_max_date`、最終取得日のヘルパ（get_last_price_date 等）
  - 市場カレンダーに基づく調整 `_adjust_to_trading_day`
  - 個別ジョブ `run_prices_etl(...)` を実装（差分算出、J-Quants fetch → save まで）

- テスト/拡張性を意識した設計
  - `news_collector._urlopen` をモック差し替え可能にしてテストが容易
  - jquants_client: id_token を外部注入できる（テスト容易性）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS フィード取得に対する SSRF 対策、XML パースの安全化、受信サイズ制限など複数のセキュリティ対策を実装

### Known issues / Notes（既知の問題・注意点）
- pipeline.run_prices_etl の実装末尾がソース内で切れており（ファイル末尾が途中で終端しているように見える）、関数の return 値が不完全に見えます（現状ソース最後の行は `return len(records),` でタプルの2要素目が欠けている可能性あり）。このままでは呼び出し側が期待する (fetched, saved) タプルを返せず、TypeError や不整合が発生する恐れがあります。リリース後の修正が必要です。
- 一部のモジュール（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py）は空のイニシャライザのみで、実装は今後追加される想定です。
- DuckDB の SQL 実行文字列は文字列連結で直に組み立てている箇所があり（プレースホルダは使われているが DDL を含む場面など）、将来的に SQL インジェクション対策やパラメータ化の統一が望まれます（現在は内部ツールとしての使用を想定）。
- RSS の GUID を代替 URL として扱う際、GUID が URL ではない場合はスキップする仕様です。メタ情報だけのフィードに対しては記事が取りこぼされる可能性があります。

---

この CHANGELOG はコードの内容から機能・設計上の意図を推測してまとめたものであり、実際の変更履歴管理（コミット単位の差分）とは異なります。実装の追加・修正が行われた場合は本ファイルも更新してください。